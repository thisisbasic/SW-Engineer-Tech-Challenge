import asyncio
import json
import logging
import os
import time

import aiohttp
from dotenv import load_dotenv
from pydicom import Dataset
from scp import ModalityStoreSCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

REST_API_URL = os.getenv("REST_API_URL", "http://127.0.0.1:8000/series/")
REFRESH_TIME_IN_SEC = int(os.getenv("REFRESH_TIME_IN_SEC", 0.2))
AE_HOST = os.getenv("AE_HOST", "127.0.0.1")
AE_PORT = int(os.getenv("AE_PORT", 6667))


class SeriesCollector:
    """A Series Collector is used to build up a list of instances (a DICOM series) as they are received by the modality.
    It stores the (during collection incomplete) series, the Series (Instance) UID, the time the series was last updated
    with a new instance and the information whether the dispatch of the series was started.
    """

    def __init__(self, first_dataset: Dataset) -> None:
        """Initialization of the Series Collector with the first dataset (instance).

        Args:
            first_dataset (Dataset): The first dataset or the regarding series received from the modality.
        """
        self.series_instance_uid = first_dataset.SeriesInstanceUID
        self.series: list[Dataset] = [first_dataset]
        self.last_update_time = time.time()
        self.dispatch_started = False

    def add_instance(self, dataset: Dataset) -> bool:
        """Add a dataset to the series collected by this Series Collector if it has the correct Series UID.

        Args:
            dataset (Dataset): The dataset to add.

        Returns:
            bool: `True`, if the Series UID of the dataset to add matched and the dataset was therefore added, `False` otherwise.
        """
        if self.series_instance_uid == dataset.SeriesInstanceUID:
            self.series.append(dataset)
            self.last_update_time = time.time()
            return True

        return False


class SeriesDispatcher:
    """This code provides a template for receiving data from a modality using DICOM.
    Be sure to understand how it works, then try to collect incoming series (hint: there is no attribute indicating how
    many instances are in a series, so you have to wait for some time to find out if a new instance is transmitted).
    For simplyfication, you can assume that only one series is transmitted at a time.
    You can use the given template, but you don't have to!
    """

    def __init__(self) -> None:
        """Initialize the Series Dispatcher."""

        self.loop: asyncio.AbstractEventLoop
        self.modality_scp = ModalityStoreSCP(host=AE_HOST, port=AE_PORT)
        self.series_collector = None
        self.maximum_wait_time_before_dispatching_in_sec = 1

    async def main(self) -> None:
        """An infinitely running method used as hook for the asyncio event loop.
        Keeps the event loop alive whether datasets are received from the modality and prints a message
        regular when no datasets are received.
        """
        while True:
            # Information about Python asyncio: https://docs.python.org/3/library/asyncio.html
            # When datasets are received you should collect and process them
            # (e.g. using `asyncio.create_task(self.run_series_collector()`)
            # logging.info("Waiting for Modality")
            await asyncio.create_task(self.run_series_collectors())
            await asyncio.sleep(REFRESH_TIME_IN_SEC)

    async def run_series_collectors(self) -> None:
        """Runs the collection of datasets, which results in the Series Collector being filled."""
        try:
            while not self.modality_scp.dataset_queue.empty():
                dataset = self.modality_scp.dataset_queue.get()
                if self.series_collector is None:
                    self.series_collector = SeriesCollector(dataset)
                elif not self.series_collector.add_instance(dataset):
                    # not your turn. Patience you must have.
                    self.modality_scp.dataset_queue.put(dataset)
                    await self.dispatch_series_collector()
            await self.dispatch_series_collector()
        except Exception as e:
            logging.error("Error in running series collector %s", e)

    async def dispatch_series_collector(self) -> None:
        """Tries to dispatch a Series Collector, i.e. to finish its dataset collection and scheduling of further
        methods to extract the desired information.
        """
        # Check if the series collector hasn't had an update for a long enough timespan and send the series to the
        # server if it is complete
        # NOTE: This is the last given function, you should create more for extracting the information and
        # sending the data to the server
        if (
            self.series_collector is not None
            and not self.series_collector.dispatch_started
        ):
            time_now = time.time()
            if (
                time_now - self.series_collector.last_update_time
            ) > self.maximum_wait_time_before_dispatching_in_sec:
                self.series_collector.dispatch_started = True
                data = self.collect_series_data()
                logging.info(
                    "Dispatching series %s with %d instances.",
                    self.series_collector.series_instance_uid,
                    data["InstancesInSeries"],
                )
                data_json = json.dumps(data)
                await self.send_post_request(REST_API_URL, data=data_json)
                self.series_collector = None

    def collect_series_data(self) -> dict:
        """Collects information about the series."""
        if not self.series_collector:
            return {}

        return {
            "SeriesInstanceUID": self.series_collector.series_instance_uid,
            "PatientName": str(self.series_collector.series[0].PatientName),
            "PatientID": self.series_collector.series[0].PatientID,
            "StudyInstanceUID": self.series_collector.series[0].StudyInstanceUID,
            "InstancesInSeries": len(self.series_collector.series),
        }

    async def send_post_request(self, url, data):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json.loads(data)) as response:
                await response.text()
                if response.status == aiohttp.http.HTTPStatus.OK:
                    logging.info("Data sent successfully %s", data)
                return response


if __name__ == "__main__":
    """Create a Series Dispatcher object and run it's infinite `main()` method in a event loop."""
    engine = SeriesDispatcher()
    engine.loop = asyncio.new_event_loop()
    engine.loop.run_until_complete(engine.main())

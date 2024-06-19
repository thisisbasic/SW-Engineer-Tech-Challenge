import time
from pathlib import Path
from unittest.mock import patch

import pytest
from pydicom import dcmread

from series.client import SeriesCollector, SeriesDispatcher


@pytest.fixture
def dispatcher():
    with patch("scp.AE.start_server") as _:
        dispatcher = SeriesDispatcher()
        return dispatcher


class Datasets:
    DATASET_1_0 = dcmread(Path(__file__).parent / "data/1/0000.dcm")
    DATASET_1_1 = dcmread(Path(__file__).parent / "data/1/0001.dcm")
    DATASET_2_1 = dcmread(Path(__file__).parent / "data/2/0001.dcm")


class TestSeriesCollector:

    def test_add_instance_same_series(self):
        with patch("time.time") as mock_time:
            mock_time.side_effect = [1000.0 + 0.1 * i for i in range(6)]
            time_before_operation = time.time()
            series_collector = SeriesCollector(Datasets.DATASET_1_0)
            time_after_operation = time.time()
            actual_series_collector_last_updated_time = (
                series_collector.last_update_time
            )
            assert (
                time_before_operation
                < actual_series_collector_last_updated_time
                < time_after_operation
            )
            assert series_collector.dispatch_started is False
            assert series_collector.series == [Datasets.DATASET_1_0]

            time_before_operation = time.time()
            series_collector.add_instance(Datasets.DATASET_1_1)
            time_after_operation = time.time()
            actual_series_collector_last_updated_time = (
                series_collector.last_update_time
            )
            assert (
                time_before_operation
                < actual_series_collector_last_updated_time
                < time_after_operation
            )
            assert series_collector.dispatch_started is False
            assert series_collector.series == [
                Datasets.DATASET_1_0,
                Datasets.DATASET_1_1,
            ]

    def test_add_instance_different_series(self):
        with patch("time.time") as mock_time:
            mock_time.side_effect = [1000.0, 1000.1, 1000.2]
            time_before_operation = time.time()
            series_collector = SeriesCollector(Datasets.DATASET_1_0)
            assert not series_collector.dispatch_started
            time_after_operation = time.time()
            actual_series_collector_last_updated_time = (
                series_collector.last_update_time
            )
            assert (
                time_before_operation
                < actual_series_collector_last_updated_time
                < time_after_operation
            )
            assert series_collector.series == [Datasets.DATASET_1_0]

            # shouldn't be added because is from different series
            series_collector.add_instance(Datasets.DATASET_2_1)
            assert not series_collector.dispatch_started
            assert (
                series_collector.last_update_time
                == actual_series_collector_last_updated_time
            )
            assert series_collector.series == [Datasets.DATASET_1_0]
            assert mock_time.call_count == 3


class TestDispatcher:
    @patch("scp.AE.start_server")
    def test_initialization(self, start_server):
        series_dispatcher = SeriesDispatcher()
        assert series_dispatcher.modality_scp is not None
        assert series_dispatcher.series_collector is None
        assert isinstance(
            series_dispatcher.maximum_wait_time_before_dispatching_in_sec, int
        )
        start_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_series_collectors(self, dispatcher):
        # @TODO: cover more scenarios
        assert dispatcher.series_collector is None
        assert dispatcher.modality_scp.dataset_queue.empty()
        dispatcher.modality_scp.dataset_queue.put(Datasets.DATASET_1_0)
        dispatcher.modality_scp.dataset_queue.put(Datasets.DATASET_1_1)

        await dispatcher.run_series_collectors()

        assert dispatcher.modality_scp.dataset_queue.empty()
        assert dispatcher.series_collector.series == [
            Datasets.DATASET_1_0,
            Datasets.DATASET_1_1,
        ]
        assert dispatcher.series_collector is not None

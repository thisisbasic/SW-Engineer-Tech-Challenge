import logging
from queue import Queue

from pydicom.dataset import FileMetaDataset
from pynetdicom import AE, events, evt, debug_logger
from pynetdicom.sop_class import MRImageStorage
from pynetdicom.status import Status

Status.add("UNABLE_TO_PROCESS", 0xC000)

debug_logger()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s",
)


class ModalityStoreSCP:
    def __init__(self, host="127.0.0.1", port=6667, block=False) -> None:
        self.ae = AE(ae_title=b"STORESCP")
        self.scp = None
        self.host = host
        self.port = port
        self.block = block
        self._dataset_queue = Queue()
        self._configure_ae()

    def _configure_ae(self) -> None:
        """Configure the Application Entity with the presentation context(s) which should be supported and start the SCP server."""
        handlers = [(evt.EVT_C_STORE, self.handle_store)]

        self.ae.add_supported_context(MRImageStorage)
        self.scp = self.ae.start_server(
            (self.host, self.port), block=self.block, evt_handlers=handlers
        )
        logging.info("SCP Server started")

    @property
    def dataset_queue(self) -> Queue:
        return self._dataset_queue

    def handle_store(self, event: events.Event) -> int:
        """Callable handler function used to handle a C-STORE event.

        Args:
            event (Event): Representation of a C-STORE event.

        Returns:
            int: Status Code
        """
        try:
            dataset = event.dataset
            dataset.file_meta = FileMetaDataset(event.file_meta)
            self._dataset_queue.put(dataset)
            logging.info("Dataset %s added in the queue", dataset.SOPInstanceUID)
            logging.debug("Queue size (estimation): %d", self._dataset_queue.qsize())
            return Status.SUCCESS
        except Exception as e:
            logging.error("Failed to process/store DICOM file %s", e)
            return Status.UNABLE_TO_PROCESS

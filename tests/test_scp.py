from unittest.mock import MagicMock, patch

import pytest
from pydicom import Dataset
from pydicom.dataset import FileMetaDataset
from pynetdicom import evt, events
from pynetdicom.sop_class import MRImageStorage
from pynetdicom.status import Status

from series.scp import ModalityStoreSCP


@pytest.fixture()
def modality_store_scp():
    with patch("series.scp.AE.start_server") as mock_start_server:
        mock_scp_server = MagicMock()
        mock_start_server.return_value = mock_scp_server
        instance = ModalityStoreSCP()
        yield instance
        instance.ae.shutdown()


class TestModalityStoreSCP:
    def test_configure_ae(self, modality_store_scp):
        modality_store_scp.ae.start_server.assert_called_once_with(
            ("127.0.0.1", 6667),
            block=False,
            evt_handlers=[(evt.EVT_C_STORE, modality_store_scp.handle_store)],
        )
        expected_contexts = [MRImageStorage]
        expected_active_associations = []
        actual_contexts = [
            context.abstract_syntax
            for context in modality_store_scp.ae.supported_contexts
        ]
        assert modality_store_scp.ae.active_associations == expected_active_associations
        assert len(actual_contexts) == len(expected_contexts)
        assert set(actual_contexts) == set(expected_contexts)

    @patch("series.scp.FileMetaDataset")
    def test_handle_store_success(self, mock_file_meta, modality_store_scp):
        modality_store_scp.ae.start_server.assert_called_once()
        mock_event = MagicMock(spec=events.Event)

        mock_dataset = Dataset()
        mock_dataset.SOPInstanceUID = "1.2.840.10008.1.1"
        mock_event.dataset = mock_dataset
        mock_file_meta.return_value = FileMetaDataset()

        status = modality_store_scp.handle_store(mock_event)

        assert status == Status.SUCCESS
        assert modality_store_scp.dataset_queue.get() == mock_event.dataset

    def test_handle_store_failure(self, modality_store_scp):
        modality_store_scp.ae.start_server.assert_called_once()
        mock_event = MagicMock(spec=events.Event)
        status = modality_store_scp.handle_store(mock_event)

        assert status == Status.UNABLE_TO_PROCESS
        assert modality_store_scp.dataset_queue.empty()

import pytest
from app.validation.state_transitions import StateTransitionValidator
from app.models.invoice import InvoiceStatus


class TestStateTransitions:
    def test_valid_transition_uploaded_to_processing(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.UPLOADED, InvoiceStatus.PROCESSING
        )
        assert can_transition is True
        assert error == ""
    
    def test_valid_transition_processing_to_processed(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.PROCESSING, InvoiceStatus.PROCESSED
        )
        assert can_transition is True
        assert error == ""
    
    def test_valid_transition_processed_to_approved(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.PROCESSED, InvoiceStatus.APPROVED
        )
        assert can_transition is True
        assert error == ""
    
    def test_valid_transition_approved_to_rpa_queued(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.APPROVED, InvoiceStatus.RPA_QUEUED
        )
        assert can_transition is True
        assert error == ""
    
    def test_valid_transition_rpa_queued_to_rpa_processing(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.RPA_QUEUED, InvoiceStatus.RPA_PROCESSING
        )
        assert can_transition is True
        assert error == ""
    
    def test_valid_transition_rpa_processing_to_rpa_completed(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.RPA_PROCESSING, InvoiceStatus.RPA_COMPLETED
        )
        assert can_transition is True
        assert error == ""
    
    def test_invalid_transition_approved_to_processing(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.APPROVED, InvoiceStatus.PROCESSING
        )
        assert can_transition is False
        assert "Invalid transition" in error
    
    def test_invalid_transition_rejected_to_approved(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.REJECTED, InvoiceStatus.APPROVED
        )
        assert can_transition is False
        assert "Invalid transition" in error
    
    def test_valid_transition_rpa_failed_to_rpa_queued(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.RPA_FAILED, InvoiceStatus.RPA_QUEUED
        )
        assert can_transition is True
        assert error == ""
    
    def test_valid_transition_error_to_processing(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.ERROR, InvoiceStatus.PROCESSING
        )
        assert can_transition is True
        assert error == ""
    
    def test_same_state_transition(self):
        can_transition, error = StateTransitionValidator.validate_transition(
            InvoiceStatus.PROCESSING, InvoiceStatus.PROCESSING
        )
        assert can_transition is True  # Same state is allowed
        assert error == ""

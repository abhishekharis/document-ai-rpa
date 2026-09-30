from app.models.invoice import InvoiceStatus


class StateTransitionValidator:
    """Validates state transitions for invoices."""
    
    VALID_TRANSITIONS = {
        InvoiceStatus.UPLOADED: [InvoiceStatus.PROCESSING, InvoiceStatus.ERROR],
        InvoiceStatus.PROCESSING: [InvoiceStatus.PROCESSED, InvoiceStatus.NEEDS_REVIEW, InvoiceStatus.ERROR],
        InvoiceStatus.PROCESSED: [InvoiceStatus.NEEDS_REVIEW, InvoiceStatus.APPROVED, InvoiceStatus.REJECTED],
        InvoiceStatus.NEEDS_REVIEW: [InvoiceStatus.APPROVED, InvoiceStatus.REJECTED, InvoiceStatus.PROCESSING],  # Reprocess
        InvoiceStatus.APPROVED: [InvoiceStatus.RPA_QUEUED],
        InvoiceStatus.REJECTED: [InvoiceStatus.PROCESSING],  # Reprocess
        InvoiceStatus.RPA_QUEUED: [InvoiceStatus.RPA_PROCESSING],
        InvoiceStatus.RPA_PROCESSING: [InvoiceStatus.RPA_COMPLETED, InvoiceStatus.RPA_FAILED],
        InvoiceStatus.RPA_COMPLETED: [],
        InvoiceStatus.RPA_FAILED: [InvoiceStatus.RPA_QUEUED],  # Retry
        InvoiceStatus.ERROR: [InvoiceStatus.PROCESSING],  # Retry
    }
    
    @classmethod
    def can_transition(cls, current_status: InvoiceStatus, new_status: InvoiceStatus) -> bool:
        """Check if a state transition is valid."""
        if current_status not in cls.VALID_TRANSITIONS:
            return False
        
        return new_status in cls.VALID_TRANSITIONS[current_status]
    
    @classmethod
    def validate_transition(cls, current_status: InvoiceStatus, new_status: InvoiceStatus) -> tuple[bool, str]:
        """
        Validate a state transition and return (is_valid, error_message).
        """
        if current_status == new_status:
            return True, ""
        
        if not cls.can_transition(current_status, new_status):
            return False, f"Invalid transition from {current_status.value} to {new_status.value}"
        
        return True, ""

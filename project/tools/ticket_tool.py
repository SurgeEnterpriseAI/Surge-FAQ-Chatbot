import random
from pydantic import BaseModel, Field
from typing import Dict, Any

def create_ticket(issue: str, customer_email: str) -> str:
    """Create a customer support ticket in the ticketing system.
    
    Args:
        issue: Brief description of the issue.
        customer_email: Contact email of the customer.
    """
    if not issue or not customer_email:
        return "Error: Issue description and customer email are required to create a ticket."
    
    ticket_id = random.randint(10000, 99999)
    return f"Success: Support ticket #{ticket_id} has been created for {customer_email} regarding: '{issue}'. A support agent will contact you shortly."

class TicketTool:
    """Tool to create a customer support ticket in the ticketing system."""
    class InputSchema(BaseModel):
        issue: str = Field(..., description="Brief description of the issue.")
        customer_email: str = Field(..., description="Contact email of the customer.")

    class OutputSchema(BaseModel):
        result: str = Field(..., description="The ticket creation result details.")

    def invoke(self, issue: str, customer_email: str) -> str:
        try:
            return create_ticket(issue, customer_email)
        except Exception as e:
            return f"Error executing ticket tool: {str(e)}"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return self.InputSchema.model_json_schema()

    @property
    def output_schema(self) -> Dict[str, Any]:
        return self.OutputSchema.model_json_schema()

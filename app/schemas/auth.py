from pydantic import BaseModel, EmailStr

class CheckEmailIn(BaseModel):
    email: EmailStr

class CheckEmailOut(BaseModel):
    exists: bool

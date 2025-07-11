# models.py
from pydantic import BaseModel, EmailStr, constr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=6)  # type: ignore

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserIdRequest(BaseModel):
    user_id: str

class UserEmailRequest(BaseModel):
    user_email: EmailStr

class LocationPayload(BaseModel):
    job_id: int = Field(..., description="Related job identifier")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")

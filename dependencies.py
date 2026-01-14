from fastapi import Request
from crud import crud_org, crud_user

# get current user
async def get_current_user(request: Request):
    token = request.cookies.get("session_token")

    if not token:
        return None
    
    user = crud_user.get_user_by_id(token)
    return user

# get current org
async def get_current_org(request: Request):
    token = request.cookies.get("session_token")

    if not token:
        return None

    org = crud_org.get_org_by_id(token)
    return org
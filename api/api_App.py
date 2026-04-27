from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/alo-mundo", summary="Alô Mundo")
async def alo_mundo():
    return "Alou...é por mim que voce procura?"


@router.get("/", summary="Home", include_in_schema=False)
async def home():
    """Redireciona para o frontend do assistente."""
    return RedirectResponse(url="/app")
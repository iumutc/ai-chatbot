from app.config import CHANNEL_DATA_PROVIDER
from app.integrations.entegra import EntegraSyncService
from app.providers.entegra_provider import EntegraChannelProvider
from app.providers.mock_provider import MockChannelProvider


def build_channel_provider(*, entegra_service: EntegraSyncService, kb_path: str):
    if CHANNEL_DATA_PROVIDER == "entegra":
        return EntegraChannelProvider(entegra_service)
    return MockChannelProvider(kb_path=kb_path)

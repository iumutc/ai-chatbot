from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelProfile:
    name: str
    max_sentences: int
    tone: str
    formatting_rule: str


_CHANNELS = {
    "site": ChannelProfile(
        name="site",
        max_sentences=3,
        tone="yardimci ve net",
        formatting_rule="Kisa ve dogrudan yanit ver.",
    ),
    "amazon": ChannelProfile(
        name="amazon",
        max_sentences=2,
        tone="resmi ve urun odakli",
        formatting_rule="Sadece urunle ilgili bilgi ver, promosyon dili kullanma.",
    ),
    "trendyol": ChannelProfile(
        name="trendyol",
        max_sentences=2,
        tone="samimi ama profesyonel",
        formatting_rule="Kargo, iade ve urun uygunlugu bilgilerini acik yaz.",
    ),
    "hepsiburada": ChannelProfile(
        name="hepsiburada",
        max_sentences=2,
        tone="net ve guven veren",
        formatting_rule="Teknik ozellik ve teslimat bilgisini onceliklendir.",
    ),
}


def get_channel_profile(channel: str | None) -> ChannelProfile:
    if not channel:
        return _CHANNELS["site"]
    return _CHANNELS.get(channel.lower(), _CHANNELS["site"])

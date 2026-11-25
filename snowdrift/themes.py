"""Visual themes.

Every theme is the same game underneath - the same streamed ribbon of track,
the same drift physics, the same points for metres - and only changes the
palette, what lines the road and what you are riding.

Track colours are baked into each ``Station`` as it is generated, so switching
theme rebuilds the stream rather than tinting polygons on the fly.
"""


class Theme:
    __slots__ = (
        "key", "name", "blurb", "accent",
        "sky", "sky_horizon", "fog",
        "ground_far", "ground_near",
        "surface", "surface_spread", "dash", "crack",
        "bank", "bank_shade", "bank_rise", "bank_width",
        "hill_far", "hill_near", "hill_amp",
        "scenery", "palette", "prop_far", "detail_far",
        "player", "shadow", "spray",
    )

    def __init__(self, **kw):
        for name in self.__slots__:
            setattr(self, name, kw[name])


SNOW = Theme(
    key="snow",
    name="ICE RUN",
    blurb="snowmobile  \u2022  ice track  \u2022  pine forest",
    accent=(206, 232, 255),
    sky=(74, 116, 168),
    sky_horizon=(203, 216, 229),
    fog=(203, 216, 229),
    ground_far=(206, 219, 232),
    ground_near=(232, 237, 244),
    surface=(150, 178, 198),
    surface_spread=5,
    dash=(126, 156, 178),
    crack=(134, 160, 180),
    bank=(241, 247, 252),
    bank_shade=(222, 232, 242),
    bank_rise=1.55,
    bank_width=3.4,
    hill_far=(186, 202, 219),
    hill_near=(197, 211, 226),
    hill_amp=118.0,
    scenery="pine",
    prop_far=70,
    detail_far=120.0,
    palette={
        "trunk": (62, 48, 42),
        "dark": (43, 70, 62),
        "light": (236, 243, 249),
        "rock": (152, 173, 190),
        "rock_top": (232, 240, 247),
    },
    player="sled",
    shadow=(128, 154, 176),
    spray=(252, 253, 255),
)

CITY = Theme(
    key="city",
    name="CITY RUN",
    blurb="snowmobile  \u2022  asphalt  \u2022  skyscrapers",
    accent=(255, 214, 152),
    sky=(58, 76, 108),
    sky_horizon=(216, 200, 186),
    fog=(214, 202, 190),
    ground_far=(184, 178, 172),
    ground_near=(206, 200, 194),
    surface=(84, 88, 96),
    surface_spread=4,
    dash=(226, 204, 124),
    crack=(116, 120, 128),
    bank=(178, 180, 184),
    bank_shade=(146, 149, 156),
    bank_rise=0.55,
    bank_width=1.8,
    hill_far=(120, 132, 152),
    hill_near=(142, 152, 170),
    hill_amp=44.0,
    scenery="city",
    prop_far=58,
    detail_far=110.0,
    palette={
        "wall": (198, 190, 178),
        "side": (168, 161, 150),
        "roof": (106, 104, 112),
        "window": (250, 226, 152),
    },
    player="sled",
    shadow=(96, 100, 108),
    spray=(214, 218, 224),
)

DIRT = Theme(
    key="dirt",
    name="DIRT RUN",
    blurb="bicycle  \u2022  dirt road  \u2022  bamboo",
    accent=(226, 236, 170),
    sky=(104, 138, 150),
    sky_horizon=(212, 214, 188),
    fog=(206, 206, 184),
    ground_far=(170, 152, 118),
    ground_near=(190, 174, 136),
    surface=(154, 128, 92),
    surface_spread=6,
    dash=(178, 152, 110),
    crack=(140, 116, 84),
    bank=(138, 114, 82),
    bank_shade=(116, 96, 68),
    bank_rise=0.8,
    bank_width=2.4,
    hill_far=(122, 144, 112),
    hill_near=(140, 164, 126),
    hill_amp=72.0,
    scenery="bamboo",
    prop_far=72,
    detail_far=112.0,
    palette={
        "stalk": (172, 178, 108),
        "leaf": (88, 126, 66),
    },
    player="bike",
    shadow=(96, 84, 60),
    spray=(208, 188, 150),
)

THEMES = (SNOW, CITY, DIRT)
current = SNOW


def index_of(which):
    """Theme index from a name, a 1-based number, or an index."""
    if isinstance(which, Theme):
        return THEMES.index(which)
    if isinstance(which, int):
        return which % len(THEMES)
    text = str(which).strip().lower()
    for i, theme in enumerate(THEMES):
        if text == theme.key or text == theme.name.lower():
            return i
    if text.isdigit():
        return (int(text) - 1) % len(THEMES)
    return 0


def set_theme(which):
    global current
    current = THEMES[index_of(which)]
    return current

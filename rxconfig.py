import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="simulador",
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="dark", accent_color="violet", radius="large"),
        ),
    ],
    disable_plugins=[SitemapPlugin],
)

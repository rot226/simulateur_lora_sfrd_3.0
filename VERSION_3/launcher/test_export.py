import panel as pn
pn.extension()
btn = pn.widgets.FileDownload(
    label="Télécharger",
    filename="test.txt",
    callback=lambda: b"ok",
    as_bytes=True
)
pn.Column(pn.pane.Markdown("Ceci est un test"), btn).servable()

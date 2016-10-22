from src.decorators import hook

### Server PING handling

@hook("ping")
def on_ping(cli, prefix, server):
    cli.send("PONG", server)

from src.decorators import hook
from src.context import Features

### Server PING handling

@hook("ping")
def on_ping(cli, prefix, server):
    cli.send("PONG", server)

### Fetch and store server information

@hook("featurelist")
def get_features(cli, rawnick, *features):
    """Fetch and store the IRC server features."""

    for feature in features:
        if "=" in feature:
            name, data = feature.split("=")
            if ":" in data:
                Features[name] = {}
                for param in data.split(","):
                    param, value = param.split(":")
                    if param.isupper():
                        settings = [param]
                    else:
                        settings = param

                    for setting in settings:
                        if value.isdigit():
                            value = int(value)
                        elif not value:
                            value = None
                        Features[name][setting] = value

            elif "(" in data and ")" in data:
                gen = (x for y in data.split("(") for x in y.split(")") if x)
                # Reverse the order
                value = next(gen)
                Features[name] = dict(zip(next(gen), value))

            elif "," in data:
                Features[name] = data.split(",")

            else:
                if data.isdigit():
                    data = int(data)
                elif not data.isalnum() and "." not in data:
                    data = frozenset(data)
                Features[name] = data

        else:
            Features[name] = None

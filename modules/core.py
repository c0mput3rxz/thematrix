from datetime import datetime
from mud.module import Module
from mud.collection import Collection, Entity, FileStorage
from mud.inject import inject
from utils.ansi import pad_right
from utils.hash import get_random_hash
from mud.timer_manager import TimerManager

import gevent
import settings
import logging


class Map(object):
    @classmethod
    def from_actor(cls, actor, width=45, height=23, border=False):
        # Note: All coordinates are (row, col) to make things easier later.
        Rooms = actor.game.get_injector("Rooms")

        VERTICAL_SYMBOL = "|"
        HORIZONTAL_SYMBOL = "--"

        VALID_DIRECTIONS = set(["north", "east", "south", "west"])

        DIRECTIONS = {
            "north": (((VERTICAL_SYMBOL,),), -1, 0, -2, 0),
            "east": (((HORIZONTAL_SYMBOL,),), 0, 1, 0, 3),
            "south": (((VERTICAL_SYMBOL,),), 1, 0, 2, 0),
            "west": (((HORIZONTAL_SYMBOL,),), 0, -2, 0, -3),
        }

        ORIGIN_COLOR = "{R"
        ROOM_COLOR = "{C"
        LINEAR_LINK_COLOR = "{x"
        NON_LINEAR_LINK_COLOR = "{r"
        EMPTY_SYMBOL = " "

        grid = [
            [EMPTY_SYMBOL for _ in range(width)] for _ in range(height)
        ]

        start_room = actor.room
        used_room_vnums = set([start_room.vnum])
        stack = [
            (height // 2, width // 2, start_room)
        ]

        def coords_are_valid(y, x):
            return y > 0 and y < height and x > 0 and x < width

        while stack:
            base_y, base_x, room = stack.pop()

            linear = True
            if grid[base_y][base_x] != EMPTY_SYMBOL:
                linear = False

            # Origin room.
            if grid[base_y][base_x] == EMPTY_SYMBOL:
                grid[base_y][base_x] = (ORIGIN_COLOR + "@") \
                    if room == start_room else (ROOM_COLOR + "#")

            for direction_id, entry in room.exits.items():
                if direction_id not in VALID_DIRECTIONS:
                    continue

                symbols, symbol_y_start, symbol_x_start, y_mod, x_mod = \
                    DIRECTIONS[direction_id]

                # Linkages.
                for symbol_y, symbol_row in enumerate(symbols):
                    for symbol_x, symbols_in_row in enumerate(symbol_row):
                        for char_x, symbol in enumerate(symbols_in_row):
                            y = base_y + symbol_y_start + symbol_y
                            x = base_x + symbol_x_start + symbol_x + char_x

                            if not coords_are_valid(y, x):
                                continue

                            link_color = LINEAR_LINK_COLOR if linear \
                                else NON_LINEAR_LINK_COLOR
                            grid[y][x] = link_color + symbol

                next_y = base_y + y_mod
                next_x = base_x + x_mod

                if not coords_are_valid(next_y, next_x):
                    continue

                next_room = Rooms.get({"vnum": entry["room_vnum"]})

                if next_room.vnum not in used_room_vnums:
                    used_room_vnums.add(next_room.vnum)
                    stack.append((next_y, next_x, next_room))

        if border:
            CORNER_SYMBOL = "{x+"
            HORIZONTAL_SYMBOL = "{x-"
            VERTICAL_SYMBOL = "{x|"

            max_y = height - 1
            max_x = width - 1

            # Corner symbols
            for y, x in ((0, 0), (0, max_x), (max_y, 0), (max_y, max_x)):
                grid[y][x] = CORNER_SYMBOL

            # Horizontals
            for x in range(1, width - 1):
                grid[max_y][x] = grid[0][x] = HORIZONTAL_SYMBOL

            # Verticals
            for y in range(1, height - 1):
                grid[y][max_x] = grid[y][0] = VERTICAL_SYMBOL

        return Map(grid)

    def __init__(self, grid):
        self.grid = grid

    def to_lines(self):
        return ["".join(row) for row in self.grid]


def equipment_command(self, **kwargs):
    self.echo("You are using:")
    self.echo("Nothing.")


def inventory_command(self, **kwargs):
    self.echo("You are carrying:")
    self.echo("     Nothing.")


def group_command(self, **kwargs):
    self.echo("{}'s group:".format(self.name))

    self.echo("[{} {}] {} {}/{} hp {}/{} mana {} xp".format(
        self.level,
        self.classes[0].short_name,

        self.name.ljust(20),

        0, 0,
        0, 0,

        self.experience,
    ))


@inject("Areas")
def asave_command(self, args, Areas, **kwargs):
    """Save the area to its storage."""

    if args:
        area_vnum = args.pop(0)
        area = Areas.get({"vnum": area_vnum})
    else:
        area = self.room.area

    if not area:
        self.echo("Area not found.")
        return

    area.save()

    self.echo("Area {} saved.".format(area.vnum))


@inject("Scripts")
def scripts_command(self, args, Scripts, **kwargs):
    """Display the list of Scripts for an Area."""

    if args:
        area_vnum = args.pop(0)
        area = Areas.get({"vnum": area_vnum})
    else:
        area = self.room.area

    area = self.room.area
    self.echo("Scripts in {}".format(area.vnum))
    for script in Scripts.query({"area_vnum": area.vnum}):
        self.echo("* {} - {} - {}".format(
            script.id, script.vnum, script.name))


@inject("Characters")
def tell_command(self, args, Characters, **kwargs):
    """Private message a Character with a message."""
    if not args:
        self.echo("Tell whom what?")
        return

    target_name = args.pop(0).lower()

    if not args:
        self.echo("Tell them what?")
        return

    message = " ".join(args)

    if target_name in settings.SELF_NAMES:
        char = self
    else:
        char = Characters.fuzzy_get(target_name)
        if not char:
            self.echo("Can't find that player.")
            return

    self.echo("{{gYou tell {} '{{G{}{{g'{{x".format(char.name, message))
    if char != self:
        char.echo("{{g{} tells you '{{G{}{{g'{{x".format(self.name, message))


def map_command(self, **kwargs):
    """Display a Map to the Character."""
    map = Map.from_actor(self)

    self.echo("{}'s Map of {}".format(
        self.name, self.room.area.name).center(79))
    self.echo("\n".join(map.to_lines()))


def time_command(self, **kwargs):
    """Display the current time."""

    now = datetime.now()

    date_format = "%a %b %d %H:%M:%S %Y"
    # great_realms_time = "Wed Dec 20 22:02:27 2017"

    current_time = now.strftime(date_format)

    self.echo("""\
{{B+{{b---------------------------------------------------------{{B+{{x
  Great Realms Standard Time: {}
{{B+{{b---------------------------------------------------------{{B+{{x
  Waterdeep Standard Time:    {}
  Waterdeep Last Rebooted:    {}
{{B+{{b---------------------------------------------------------{{B+{{x\
""".format(
        current_time,
        current_time,
        current_time,
    ))

    pass


@inject("Rooms", "Areas")
def rooms_command(self, args, Rooms, Areas, **kwargs):

    if args:
        area_vnum = args.pop(0)
        area = Areas.get({"vnum": area_vnum})
    else:
        area = self.room.area

    if not area:
        self.echo("Area {} not found.".format(area_vnum))
        return

    self.echo("Rooms in {}".format(area.vnum))

    count = 0
    for room in Rooms.query({"area_id": area.id}):
        count += 1
        self.echo("* {} - {} - {}{{x".format(room.id, room.vnum, room.name))

    if count == 0:
        self.echo("No rooms found.")


@inject("Areas")
def areas_command(self, Areas, **kwargs):
    """List all Areas available in the Game."""
    self.echo("List of Areas:")
    for area in Areas.query():
        self.echo("* {} - {} - {}".format(area.id, area.vnum, area.name))


@inject("Rooms")
def goto_command(self, args, Rooms, **kwargs):
    """Go to a certain Room by its ID or VNUM."""
    if not args:
        self.echo("Please specify a room ID or VNUM.")
        return

    room_id_or_vnum = args.pop(0)
    room = Rooms.fuzzy_get(room_id_or_vnum)

    if not room:
        self.echo("Room not found.")
        return

    self.act("{self.name} disappears suddenly.")
    self.room_id = room.id
    self.room_vnum = room.vnum
    self.save()
    self.act("{self.name} appears suddenly.")
    self.force("look")


def fail_command(self, **kwargs):
    """Force an Exception to occur."""
    raise Exception("Testing exceptions.")


def channel_command(self, name, message, **kwargs):
    channel = settings.CHANNELS[name]

    if not message:
        self.echo("Channel toggling is not yet supported.")
        return

    def replace(template):
        template = template.replace("{name}", self.name)
        template = template.replace("{message}", message)
        return template

    template_to_others = channel["to_others"]

    self.echo(replace(channel.get("to_self", template_to_others)))
    self.game.echo(replace(template_to_others), exclude=[self])


@inject("Directions", "Rooms")
def unlink_command(self, args, Directions, Rooms, **kwargs):
    if not args:
        self.echo("Link which exit to which room?")
        return

    direction_id = args.pop(0)
    direction = Directions.fuzzy_get(direction_id)

    if not direction:
        self.echo("That's not a valid direction.")
        return

    room = self.room

    if not room.exits.get(direction.id, None):
        self.echo("That exit does not exist.")
        return

    other_room = Rooms.get({"vnum": room.exits[direction.id]["room_vnum"]})

    counter_exit = other_room.exits.get(direction.opposite_id, None)
    if counter_exit and counter_exit["room_vnum"] == room.vnum:
        del other_room.exits[direction.opposite_id]
        other_room.save()
        other_room.area.save()

    del room.exits[direction.id]
    room.save()
    room.area.save()

    self.echo("The link to the {} to room {} has been removed.".format(
        direction.colored_name, other_room.vnum))


@inject("Directions", "Rooms")
def link_command(self, args, Directions, Rooms, **kwargs):
    if not args:
        self.echo("Link which exit to which room?")
        return

    direction_id = args.pop(0)

    if not args:
        self.echo("Link it to which room?")
        return

    room_vnum = args.pop(0)

    direction = Directions.fuzzy_get(direction_id)
    if not direction:
        self.echo("That's not a valid direction.")
        return

    room = self.room

    if room.exits.get(direction.id, None):
        self.echo("That exit already has a room linked to it.")
        return

    other_room = Rooms.get({"vnum": room_vnum})

    if other_room.exits.get(direction.opposite_id, None):
        self.echo(
            "The other room already has an exit in the opposite direction.")
        return

    room.exits[direction.id] = {"room_vnum": other_room.vnum}
    room.save()
    room.area.save()

    other_room.exits[direction.opposite_id] = {"room_vnum": room.vnum}
    other_room.save()
    other_room.area.save()

    self.echo("A link to the {} has been created to room {}".format(
        direction.colored_name, other_room.vnum))


@inject("Areas", "Rooms", "Directions")
def dig_command(self, args, Areas, Rooms, Directions, **kwargs):
    if not args:
        self.echo("Dig in which direction?")
        return

    direction_id = args.pop(0)

    direction = Directions.fuzzy_get(direction_id)
    if not direction:
        self.echo("That's not a valid direction.")
        return

    room = self.room

    exit = room.exits.get(direction.id, None)
    if exit:
        self.echo("That direction already has an exit.")
        return

    area = room.area

    # Look up the existing Room
    if args:
        room_vnum = args.pop(0)
        new_room = Rooms.get({"vnum": room_vnum})

        if not new_room:
            self.echo("The Room VNUM you've requested does not exist.")
            return

    # Create the new Room
    else:
        new_room = Rooms.save({
            "area_id": area.id,
            "area_vnum": area.vnum,
            "vnum": get_random_hash()[:6],
            "name": "Unnamed Room",
            "description": [],
            "exits": {},
        })

    # Link the Rooms
    new_room.exits[direction.opposite_id] = {"room_vnum": room.vnum}
    new_room.save()
    room.exits[direction.id] = {"room_vnum": new_room.vnum}
    room.save()

    # Save the area.
    area.save()

    self.echo("Room {} to the {} has been created.".format(
        new_room.vnum, direction.colored_name))

    self.echo()

    self.force(direction.id)


@inject("Actors", "Objects", "Directions")
def look_command(self, args, Actors, Objects, Directions, **kwargs):
    room = self.room

    lines = []
    lines.append(
        "{{B{} {{x[{{WLAW{{x] {{R[{{WSAFE{{R]{{x".format(room["name"]))
    lines.append("(ID: {}) (VNUM: {}) (Area: {})".format(
        room["id"], room["vnum"], room["area_vnum"]))

    for index, line in enumerate(room.description):
        if index == 0:
            line = "{x   " + line
        lines.append(line)

    lines.append("")

    exit_names = []
    door_names = []

    for direction in Directions.query():
        exit = room.exits.get(direction.id, None)
        if exit:
            exit_names.append(direction.colored_name)

    exits_line = "{{x[{{GExits{{g:{{x {}{{x]   " \
        "{{x[{{GDoors{{g:{{x {}{{x]   ".format(
            " ".join(exit_names) if exit_names else "none",
            " ".join(door_names) if door_names else "none",
        )
    lines.append(exits_line)

    spec = {"room_id": room["id"]}
    for actor in Actors.query(spec):
        lines.append("{} is standing here.".format(actor["name"]))

    for obj in Objects.query(spec):
        lines.append("{} is on the ground here.".format(obj["name"]))

    MINIMAP_ENABLED = True
    MINIMAP_WIDTH = 16
    MINIMAP_HEIGHT = 8
    MINIMAP_BORDER = False
    MINIMAP_JOIN_SYMBOLS = "  "

    if MINIMAP_ENABLED:
        minimap = Map.from_actor(
            self, width=MINIMAP_WIDTH, height=MINIMAP_HEIGHT,
            border=MINIMAP_BORDER)
        map_lines = minimap.to_lines()

        map_line_count = len(map_lines)
        line_count = len(lines)

        outputs = []

        for index in range(max(map_line_count, line_count)):
            map_line = map_lines[index] if index < map_line_count else \
                " " * MINIMAP_WIDTH
            line = lines[index] if index < line_count else \
                ""

            outputs.append(map_line + MINIMAP_JOIN_SYMBOLS + line)

        lines = outputs

    self.echo(lines)


def quit_command(self, **kwargs):
    self.echo("You're logging out...")
    self.quit()


def say_command(self, message, **kwargs):
    if not message:
        self.echo("Say what?")
        return

    say_data = {"message": message}
    say = self.trigger("before:say", say_data)
    if say.blocked:
        return

    self.echo("{{MYou say {{x'{{m{}{{x'".format(message))
    self.act("{M{self.name} says {x'{m{message}{M{x'", {
        "message": message,
    })

    self.trigger("after:say", say_data, unblockable=True)


@inject("Directions", "Rooms")
def direction_command(self, name, Directions, Rooms, **kwargs):
    room = self.room

    if not room:
        self.echo("You aren't anywhere.")
        return

    exit = room.exits.get(name, None)
    if not exit:
        self.echo("You can't go that way.")
        return

    direction = Directions.get(name)

    walk_data = {"direction": name}
    walk = self.trigger("before:walk", walk_data)

    if walk.blocked:
        return

    new_room = Rooms.get({"vnum": exit["room_vnum"]})

    if not new_room:
        self.echo("The place you're walking to doesn't appear to exist.")
        return

    enter_data = {"direction": direction.opposite}
    enter = self.trigger("before:enter", enter_data)

    if enter.blocked:
        return

    self.act("{self.name} leaves " + direction.colored_name)
    self.room_id = new_room.id
    self.save()
    self.act("{self.name} has arrived.")

    self.trigger("after:enter", enter_data, unblockable=True)
    self.trigger("after:walk", walk_data, unblockable=True)

    self.force("look")

    return 0.5


def score_command(self, **kwargs):
    self.echo("{{GName{{g:{{x {} {}".format(self.name, self.title))
    self.echo("{{GExperience{{g:{{x {}".format(self.experience))


@inject("Characters")
def who_command(self, Characters, **kwargs):
    self.echo("{GThe Visible Mortals and Immortals of Waterdeep")
    self.echo("{g" + ("-" * 79))

    count = 0
    for actor in Characters.query({"online": True}):
        count += 1

        self.echo("{{x{} {} {} {} {{x[.{{BN{{x......] {} {}".format(
            str(actor.level).rjust(3),
            pad_right(actor.gender.colored_short_name, 1),
            pad_right(actor.races[0].colored_name, 5),
            pad_right(actor.classes[0].colored_short_name, 3),
            actor.name,
            actor.title if actor.title else "",
        ))
    self.echo()
    self.echo(
        "{{GPlayers found: {{x{}   "
        "{{GTotal online: {{x{}   "
        "{{GMost on today: {{x{}".format(
            count,
            count,
            count,
        ))


@inject("Characters")
def delete_command(self, Characters, **kwargs):
    self.echo("Removing your character from the game.")
    Characters.delete(self)
    self.quit(skip_save=True)


def save_command(self, **kwargs):
    self.echo("Your character has been saved.")


@inject("Characters")
def finger_command(self, args, Characters, **kwargs):
    if not args:
        self.echo("Finger whom?")
        return

    name = args.pop(0).lower().title()
    actor = Characters.get({"name": name})
    if not actor:
        self.echo("No such player: {}".format(name))
        return

    output = """ \
+-----------------------[ WaterdeepMUD Character Info ]-----------------------+
 Name {}   : {} {}
 Class    : {}                          Clan    : {}
 Race     : {}                          Rank    : {}
 Level    : {}                          Deity   : {}
 Age      : {}                          Arena   : {} Wins
 Height   : {}                                    {} Losses
 Weight   : {}                          Hours   : {}
 Hair     : {}                          Birthday: {}
 Eyes     : {}                          Old Clan: {}
 PK Rank  : {}                          NPK Rank: {}
 RP Status: {}
+-------------------------------| DESCRIPTION |-------------------------------+
{}
+-----------------------------------------------------------------------------+
{} is currently {} from {}.
+-----------------------------------------------------------------------------+\
""".format(
        actor.gender.colored_short_name,
        actor.name,
        actor.title,
        actor.classes[0].name,
        "",
        actor.races[0].name,
        "",
        str(actor.level),
        "",
        "",
        str(0),
        "",
        str(0),
        "",
        str(0),
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "\n".join(actor.description or []),
        actor.name,
        "ONLINE",
        ""
    )
    self.echo(output)


def title_command(self, message, **kwargs):
    self.title = message
    self.save()
    if message:
        self.echo("Title set to: {}".format(self.title))
    else:
        self.echo("Title cleared.")


class ActorStat(object):
    def __init__(self, id, value, actor):
        self.id = id
        self.value = value
        self.actor = actor

    @property
    def base(self):
        return self.value

    @base.setter
    def base(self, value):
        self.actor.data["stats"][self.id] = value

    @property
    def bonus(self):
        return 0

    @property
    def total(self):
        return self.base + self.bonus


class ActorStats(object):
    def __init__(self, stats, actor):
        self.stats = stats
        self.actor = actor

    def __getattr__(self, key):
        if key not in self.stats:
            self.stats[key] = 0
        return ActorStat(key, self.stats[key], self.actor)


class Actor(Entity):
    DEFAULT_DATA = {
        "name": "",
        "title": "",
        "bracket": "",
        "level": 1,
        "experience": 0,
        "room_id": "",
        "room_vnum": settings.INITIAL_ROOM_VNUM,
        "race_ids": ["human"],
        "class_ids": ["adventurer"],
    }

    @inject("Actors")
    def spawn_actor(self, data, Actors):
        room = self.room
        data["room_id"] = room.id
        data["room_vnum"] = room.vnum

        area = room.area
        data["area_id"] = area.id
        data["area_vnum"] = area.vnum

        return Actors.save(data)

    @property
    @inject("Classes")
    def classes(self, Classes):
        return [Classes.get(class_id) for class_id in self.class_ids]

    @property
    @inject("Races")
    def races(self, Races):
        return [Races.get(race_id) for race_id in self.race_ids]

    @property
    @inject("Genders")
    def gender(self, Genders):
        return Genders.get(self.gender_id)

    @property
    @inject("Rooms")
    def room(self, Rooms):
        room = Rooms.get(self.room_id)

        save_room = False
        if not room:
            save_room = True
            room = Rooms.get({"vnum": self.room_vnum})
            if not room:
                save_room = True
                room = Rooms.get({"vnum": settings.INITIAL_ROOM_VNUM})

        if not room:
            room = Rooms.get({"vnum": "void"})

        if save_room:
            self.room_id = room.id
            self.room_vnum = room.vnum
            self.save()

        return room

    @property
    def connection(self):
        return self.game.connections.get(self.connection_id, None)

    @property
    def client(self):
        if not self.connection:
            return None
        return self.connection.client

    def say(self, message):
        say_command(self, message=message)

    def save(self):
        self.collection.save(self)

    def quit(self, skip_save=False):
        if not self.client:
            return
        self.client.quit()
        self.online = False

        if not skip_save:
            self.save()

    def force(self, message):
        if not self.client:
            return
        self.client.handle_input(message)

    def echo(self, message=""):
        if not self.client:
            return

        if isinstance(message, list):
            for line in message:
                self.echo(line)
        else:
            self.client.writeln(str(message))

    def emit_event(self, event):
        return self.room.emit_event(event)

    def trigger(self, type, data=None, unblockable=False):
        event = self.generate_event(type, data, unblockable=unblockable)
        if unblockable:
            gevent.spawn(self.emit_event, event)
            return event
        else:
            return self.emit_event(event)

    def act(self, template, data=None):
        Actors, Characters = self.game.get_injectors("Actors", "Characters")
        if data is None:
            data = {}

        data["self"] = self

        room_id = self.room_id

        message = template

        for collection in (Characters, Actors):
            for actor in collection.query({"room_id": room_id}):
                if actor == self:
                    continue

                if "{message}" in message:
                    message = message.replace("{message}", data["message"])
                if "{self.name}" in message:
                    message = message.replace("{self.name}", data["self"].name)

                actor.echo(message)

    @property
    def stats(self):
        data = self.data
        if "stats" not in data:
            data["stats"] = {}
        return ActorStats(data["stats"], self)


class Account(Entity):
    pass


class Accounts(Collection):
    ENTITY_CLASS = Account
    STORAGE_CLASS = FileStorage


class Object(Entity):
    pass


class Character(Actor):
    pass


class Area(Entity):
    pass


class Areas(Collection):
    ENTITY_CLASS = Area
    STORAGE_CLASS = FileStorage

    @inject("Rooms", "Actors", "Objects", "Scripts")
    def hydrate(self, record, Rooms, Objects, Actors, Scripts):
        """Load the Area from the file."""

        # Ensure all records have the Area's information in them
        keys = ["rooms", "actors", "objects", "scripts"]
        for key in keys:
            for entity in record[key]:
                entity["area_vnum"] = record["vnum"]
                entity["area_id"] = record["id"]

        # Save all attached records
        [Rooms.save(room) for room in record.pop("rooms")]
        [Objects.save(obj) for obj in record.pop("objects")]
        [Actors.save(actor) for actor in record.pop("actors")]
        [Scripts.save(script) for script in record.pop("scripts")]

        return record

    @inject("Rooms", "Actors", "Objects", "Scripts")
    def dehydrate(self, record, Rooms, Actors, Objects, Scripts):
        """Save the Area to a file."""

        query_args = [{"area_vnum": record["vnum"]}]
        query_kwargs = {"as_dict": True}

        record["rooms"] = list(Rooms.query(*query_args, **query_kwargs))
        record["actors"] = list(Actors.query(*query_args, **query_kwargs))
        record["objects"] = list(Objects.query(*query_args, **query_kwargs))
        record["scripts"] = list(Scripts.query(*query_args, **query_kwargs))

        scrub_keys = ["area_id", "area_vnum"]
        keys = ["rooms", "actors", "objects", "scripts"]
        for key in keys:
            for entity in record[key]:
                for scrub_key in scrub_keys:
                    if scrub_key in entity:
                        del entity[scrub_key]

        return record

    def post_delete(self, record):
        """Remove all related Entities."""
        pass


class Room(Entity):
    DEFAULT_DATA = {
        "name": "",
        "exits": {},
        "description": [],
    }

    @property
    @inject("Actors", "Characters", "Objects")
    def children(self, Actors, Characters, Objects):
        # TODO Make this flexible, to define model relationships?
        for collection in (Actors, Characters, Objects):
            for entity in collection.query({"room_id": self.id}):
                yield entity

    def emit_event(self, event):
        """Handle the Event for this level and its children, then emit up."""
        for entity in self.children:
            event = entity.handle_event(event)

            if event.blocked:
                return event

        # TODO get the event back from the Area
        event = self.handle_event(event)

        return event

    @property
    @inject("Areas")
    def area(self, Areas):
        """Get the Room's Area."""
        return Areas.get(self.area_id) or Areas.get({"vnum": self.area_vnum})


class Direction(Entity):
    pass


class Rooms(Collection):
    ENTITY_CLASS = Room

    @inject("Areas")
    def fuzzy_get(self, identifier, Areas):
        """Try to find a Room by its id, strict vnum, loose vnum."""
        # Try ID
        room = self.get(identifier)
        if room:
            return room

        # If area:vnum format, try that.
        if settings.VNUM_AREA_SEPARATOR in identifier:
            parts = identifier.split(settings.VNUM_AREA_SEPARATOR)
            area_vnum = parts[0].lower()
            room_vnum = parts[1].lower()

            area = Areas.get({"vnum": area_vnum})

            # Area does not exist.
            if not area:
                return None

            for room in self.query({"area_vnum": area.vnum}):
                if room.vnum.startswith(room_vnum):
                    return room

        # Fuzzy scan the world.
        else:
            room_vnum = identifier.lower()

            for room in self.query():
                if room.vnum.startswith(room_vnum):
                    return room


class Script(Entity):
    def execute(self, entity, event):
        try:
            compiled = \
                compile(self.code, "script:{}".format(self.id), "exec")

            def wait(duration):
                gevent.sleep(duration)

            context = dict(event.data)
            context.update({
                "self": entity,
                "target": event.source,
                "event": event,
                "wait": wait,
            })

            exec(compiled, context, context)
        except Exception as e:
            self.game.handle_exception(e)


class Scripts(Collection):
    ENTITY_CLASS = Script


class Behavior(Entity):
    @property
    @inject("Scripts")
    def script(self):
        return Scripts.get({"vnum": self.script_vnum})


class Behaviors(Collection):
    ENTITY_CLASS = Behavior
    STORAGE_CLASS = FileStorage


class Characters(Collection):
    STORAGE_CLASS = FileStorage
    STORAGE_FILENAME_FIELD = "name"
    ENTITY_CLASS = Character

    def fuzzy_get(self, name, online=True, visible=True):
        filters = {}

        name = name.lower()

        if online:
            filters["online"] = True

        first_match = None

        for char in self.query({"online": online}):
            char_name = char.name.lower()
            if char_name == name:
                return char

            if char_name.startswith(name):
                first_match = char

        return first_match


class Genders(Collection):
    ENTITY_CLASS = Entity
    STORAGE_CLASS = FileStorage


class Classes(Collection):
    ENTITY_CLASS = Entity
    STORAGE_CLASS = FileStorage


class Races(Collection):
    ENTITY_CLASS = Entity
    STORAGE_CLASS = FileStorage


class Actors(Collection):
    ENTITY_CLASS = Actor


class Objects(Collection):
    pass


class Directions(Collection):
    STORAGE_CLASS = FileStorage
    ENTITY_CLASS = Direction

    def fuzzy_get(self, name):
        name = name.lower()
        for direction in self.query():
            if direction.id.startswith(name):
                return direction


class TickManager(TimerManager):
    TIMER_DELAY = settings.TICK_SECONDS

    def tick(self):
        self.game.trigger("before:tick", blockable=False)
        logging.debug("Tick.")
        self.game.trigger("after:tick", blockable=False)


class CoreModule(Module):
    DESCRIPTION = "The basics of the game, primarily data models"

    def __init__(self, game):
        super(CoreModule, self).__init__(game)
        self.game.register_injector(Rooms)
        self.game.register_injector(Actors)
        self.game.register_injector(Objects)
        self.game.register_injector(Characters)
        self.game.register_injector(Directions)
        self.game.register_injector(Scripts)
        self.game.register_injector(Behaviors)
        self.game.register_injector(Genders)
        self.game.register_injector(Classes)
        self.game.register_injector(Races)
        self.game.register_injector(Areas)

        for dir_name in settings.DIRECTIONS:
            self.game.register_command(dir_name, direction_command)

        for channel_name in settings.CHANNELS:
            self.game.register_command(channel_name, channel_command)

        self.game.register_command("look", look_command)
        self.game.register_command("who", who_command)
        self.game.register_command("title", title_command)
        self.game.register_command("score", score_command)
        self.game.register_command("delete", delete_command)
        self.game.register_command("say", say_command)
        self.game.register_command("quit", quit_command)
        self.game.register_command("fail", fail_command)
        self.game.register_command("dig", dig_command)
        self.game.register_command("link", link_command)
        self.game.register_command("unlink", unlink_command)
        self.game.register_command("areas", areas_command)
        self.game.register_command("goto", goto_command)
        self.game.register_command("rooms", rooms_command)
        self.game.register_command("time", time_command)
        self.game.register_command("map", map_command)
        self.game.register_command("scripts", scripts_command)
        self.game.register_command("tell", tell_command)
        self.game.register_command("asave", asave_command)
        self.game.register_command("equipment", equipment_command)
        self.game.register_command("inventory", inventory_command)
        self.game.register_command("group", group_command)
        self.game.register_command("finger", finger_command)

        self.game.register_manager(TickManager)

        directions, characters, rooms, areas = \
            self.game.get_injectors(
                "Directions", "Characters", "Rooms", "Areas")

        directions.data = settings.DIRECTIONS

        for actor in characters.query():
            actor.online = False
            actor.connection_id = None
            characters.save(actor)

        areas.save({
            "id": "void",
            "vnum": "void",
            "name": "The Void",
        })

        rooms.save({
            "id": "void",
            "vnum": "void",
            "area_vnum": "void",
            "name": "The Void",
            "description": [
                "You are floating in nothingness.",
            ],
            "exits": {},
        })

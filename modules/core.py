"""
EXAMPLE MODULE
"""
import hashlib
import json
from glob import glob
from utils.entity import Entity
from utils.ansi import Ansi
from utils.collection import GameCollection, Index, CollectionEntity
from mud.module import Module
from mud.manager import Manager
from utils.listify import listify
import logging
import random
from settings import DIRECTIONS, CHANNELS, SOCIALS



def score_command(self):
    """Display the Player's Character scoresheet."""
    lines = []
    lines.append("{GName{g: {x%s %s" % (self.name, self.get("title", "")))

    lines.append("{GDesc{g:{x %s %s %s %s %s {GLevel{g: {x%d {GAge{g:{x %d" % (
        "True", "Neutral", "Male", "Heucuva", "Priest", 101, 306
    ))

    lines.append("{GHP{g:{x%d{g/{x%d {g({c%d{g) {GMana{g:{x%d{g/{x%d {g({c%d{g) {GMove{g:{x%d{g/{x%d {g({c%d{g) {GSaves{g:{x%d" % (
        8206, 8206, 2794, 11092, 11092, 10132, 1248, 1248, 998, -66
    ))

    lines.append("{g------------+-----------------------+---------------{x")
    lines.append("{GStr{g: {x%d{g({x%d{g) {g| {GItems{g:     {x%d{g/{x%d     {g| {GHitroll{g: {x%d" % (
        25, 25, 25, 125, 255
    ))
    lines.append("{GInt{g: {x%s{g({x%s{g) | {GWeight{g:    {x%s{g/ {x%s     {g| {GDamroll{g: {x%s" % (25, 25, 20, 72, 285))
    lines.append("{GWis{g: {x%s{g({x%s{g) +----------------+------+---------------" % (25, 25))
    lines.append("{GDex{g: {x%s{g({x%s{g) | {GPractices{g:  {x%s {g| {GArena Wins{g:     {x%s" % (25, 25, 10, 0))
    lines.append("{GCon{g: {x%s{g({x%s{g) | {GTrains{g:     {x%s {g| {GArena Losses{g:   {x%s" % (25, 25, 10, 0))
    lines.append("{g------------+---------+------+----------------------")
    lines.append("{GCoins Platinum{g:    {x%s {g| {GExperience" % (10))
    lines.append("      {GGold{g:        {x%s {g|  {GCurrent{g: {x%s" % (10, 10000000))
    lines.append("      {GSilver{g:      {x%s {g| {GAdventure Points{g: {x%s" % (10, 100))
    lines.append("{g----------------------+-----------------------------")
    lines.append("{GArmor Pierce{g:  {x%d [%s{x]" % (123, "super armored"))
    lines.append("      {GBash{g:    {x%d [%s{x]" % (123, "super armored"))
    lines.append("      {GSlash{g:   {x%d [%s{x]" % (123, "super armored"))
    lines.append("      {GMagic{g:   {x%d [%s{x]" % (123, "super armored"))
    lines.append("{g----------------+-------------+---------------------")
    lines.append("{GAlignment{g:   {x%d {g| {GWimpy{g:    {x%d {g| {GQuest Points{g: {x%d" % (49, 0, 1984))

    lines.append("{g----------------+-------------+---------------------{x")
    lines.append("{GPkStatus{g: {x%s{x" % ("PK"))
    lines.append("{g----------------------------------------------------{x")

    output = "\n".join(lines)
    self.echo(output)

def scrollify(lines, header=""):
    output = """\
  __________________________________________________________________________
 /\\_\\                                                                     \\_\\
|/\\\\_\\""" + header.center(69)+ """\\_\\
\\_/_|_|                                                                     |_|
"""
    for line in lines:
        output += "    |_| " + line.center(67, " ") + " |_|"
    output += """
 ___|_|                                                                     |_|
/ \\ |_|                                                                     |_|
|\\//_/                                                                     /_/
 \\/_/_____________________________________________________________________/_/
"""
    return output


def wizlist_command(self, Characters):
    """List the Immortals."""
    names = [char.name for char in Characters.query() if char.is_immortal()]
    self.echo(scrollify(names, header="Gods and Rulers Of Waterdeep"))


def channel_command(self, message):
    """Echo a Channel to the Game."""
    parts = message.split(" ")
    channel_name = parts.pop(0)
    message = " ".join(parts)

    if not message:
        self.echo("Channel toggling is not yet supported.")
        return


    channel = None
    for channel_id, entry in CHANNELS.items():
        if channel_id.startswith(channel_name):
            channel = entry
            break

    game = self.get_game()

    template = channel.get("format", "")
    self.gecho(template.format(actor=self, message=message), exclude=self)

    self_template = channel.get("self_format", template)
    self.echo(self_template.format(actor=self, message=message))


def social_command(self, message):
    """Handle an Actor performing a social emote."""
    parts = message.split(" ")
    social_name = parts.pop(0)

    target = None
    if parts:
        # TODO Figure out target
        pass

    social = None
    for social_id, entry in SOCIALS.items():
        if social_id.startswith(social_name):
            social = entry
            break

    if target is None:
        self.gecho(social["me_to_room"].format(me=self))
        self.gecho(social["actor_to_room"].format(actor=self))
        return

    if target == self:
        self.gecho(social["me_to_self"].format(me=self))
        self.gecho(social["actor_to_self"].format(actor=self))
        return

    self.gecho(social["me_to_target"].format(me=self, target=target))
    self.gecho(social["actor_to_target"].format(actor=self, target=target))
    self.gecho(social["actor_to_me"].format(actor=self, me=target))


def walk_command(self, message):
    """Walk in a direction."""
    arguments = message.split(" ")

    if not arguments:
        self.echo("Walk where?")
        return

    direction = None
    for direction_id, entry in DIRECTIONS.items():
        if direction_id.startswith(arguments[0]):
            direction = entry
            break

    if direction is None:
        self.echo("You can't walk in that direction.")
        return

    room = self.get_room()
    exit = room.get_exit(direction_id)

    if exit is None:
        self.echo("You can't walk in that direction.")
        return

    target_room = exit.get_room()
    if target_room is None:
        raise Exception("Room does not exist for exit {} in room {}".format(
            direction_id,
            room.id
        ))

    self.set_room(target_room)
    self.save()
    self.handle_command("look")


def sockets_command(self):
    """List the socket Connections."""
    game = self.get_game()
    connections = game.get_connections()
    self.echo("[Port  Num Connected_State Login@ Idle] Player Name Host")
    self.echo("-" * 79)
    count = 0

    for conn in connections:
        count += 1
        state = "handshaking"
        actor_name = "UNKNOWN"
        client = conn.get_client()

        if client:
            state = client.state
            actor = client.get_actor()
            if actor:
                actor_name = actor.name

        self.echo("[%3d %15s %7s %3d] %s %s (%s) %s" % (
            count,
            state,
            "00:00XX",
            0,
            actor_name,
            conn.hostname,
            conn.ip,
            conn.TYPE
        ))

    self.echo()
    self.echo("%d users" % count)

def exception_command(self):
    """Raise an Exception."""
    raise Exception("Testing exception")


def title_command(self, arguments):
    if not arguments:
        self.echo("Change your title to what?")
        return

    if arguments[0] == "clear":
        self.title = ""
        self.echo("Your title has been cleared.")
    else:
        self.title = " ".join(arguments)
        self.echo("Your title has been set to: %s{x" % self.title)

    self.save()


def who_command(self, arguments, Characters):
    total_count = 0
    visible_count = 0
    top_count = 999

    self.echo((" " * 15) + "{GThe Visible Mortals and Immortals of Waterdeep")
    self.echo("{g" + ("-" * 79))

    actors = list(Characters.query({"online": True}))
    actors = sorted(actors, key=lambda a: a.is_immortal(), reverse=True)
    for actor in actors:
        total_count += 1
        if not self.can_see(actor):
            continue

        visible_count += 1

        line = ""

        level_restring = actor.get("who_level_restring", None)
        if level_restring:
            line += level_restring + "{x"
        else:
            line += "{RIMM{x" if actor.is_immortal() else "{x  1{x"

        line += " "

        who_restring = actor.get("who_restring", None)
        if who_restring:
            line += who_restring
        else:
            gender_restring = actor.get("who_gender_restring", None)
            line += gender_restring if gender_restring else "{BM{x"

            line += " "

            race_restring = actor.get("who_race_restring", None)
            line += race_restring if race_restring else "{CH{cuman"

            line += " "

            class_restring = actor.get("who_class_restring", None)
            line += class_restring if class_restring else "{RA{rdv"

            line += " "

            clan_restring = actor.get("who_clan_restring", None)
            if clan_restring:
                line += clan_restring
            else:
                clan = actor.get_organization("clan")
                if not clan or clan.is_hidden():
                    line += " " * 5
                else:
                    line += Ansi.pad_right(clan.who_name, 5)

        line += " "

        flag_restring = actor.get("who_flags_restring", None)
        if flag_restring:
            line += "{x[%s{x]" % flag_restring
        else:
            line += ("{x[...{BN{x......]{x" if actor.is_immortal()
                     else "  {x[.{BN{x......]{x")
        line += " "
        line += actor.name

        if actor.title:
            if actor.title[0] not in ",.":
                line += " "
            line += ("{x%s{x" % actor.title) if actor.title else ""

        for bracket in actor.get("who_brackets", []):
            line += (" {x[%s{x]" % bracket)

        self.echo(line)

    self.echo()
    self.echo(("{GPlayers found{g: {x%s   " % visible_count) +
              ("{GTotal online{g: {W%s   " % total_count) +
              ("{GMost on today{g: {x%s" % top_count))


def swear_command(self, arguments):
    self.echo("Testing swear filter: fuck Fuck FUCK fUcK fuCK? !!Fuck!!")


LOOK_ACTOR_FLAGS = (
    ("y", "V", "invisible"),
    ("8", "H", "hiding"),
    ("c", "C", "charmed"),
    ("b", "T", "pass_door"),
    ("w", "P", "faerie_fire"),
    ("C", "I", "iceshield"),
    ("r", "I", "fireshield"),
    ("B", "L", "shockshield"),
    ("R", "E", "evil"),
    ("Y", "G", "good"),
    ("W", "S", "sanctuary"),
    ("G", "Q", "immortal_quest"),
)


def look_command(self, arguments, Characters, Actors):
    from settings import SELF_KEYWORDS

    def format_actor_flags(actor):
        flag_found = False
        flags = ""
        for color, symbol, flag_id in LOOK_ACTOR_FLAGS:
            if not actor.has_flag(flag_id):
                symbol = "."
            else:
                flag_found = True
            flags += "{%s%s" % (color, symbol)

        if flag_found:
            return "{x[%s{x] " % flags
        return ""

    def format_actor(actor):
        return "%s%s is here{x" % (
            format_actor_flags(actor),
            actor.format_name_to(self)
        )

    room = self.get_room()

    def look_at_actor(target):
        for index, line in enumerate(target.get("description", [
            "You see nothing special about %s." % target.name
        ])):
            self.echo(("{C" + line) if index == 0 else line)
        self.echo("{x%s{x {Ris in excellent condition.{x" % (
            target.name
        ))

    if arguments:
        keyword = arguments[0]

        if keyword in SELF_KEYWORDS:
            look_at_actor(self)
            return

        targets = [
            Characters.query({"room_id": room.id, "online": True}),
            Actors.query({"room_id": room.id}),
        ]
        for actors in targets:
            for actor in actors:
                if self.can_see(actor) and actor.matches_keywords(keyword):
                    look_at_actor(actor)
                    return

        self.echo("You don't see that here.")
        return

    self.echo("{B%s{x" % room.name)

    for index, line in enumerate(room.description):
        if index == 0:
            self.echo("{x  " + line)
        else:
            self.echo(line)

    self.echo()

    basic_exits = []
    door_exits = []
    secret_exits = []

    for direction_id, direction in DIRECTIONS.items():
        exit = room.get_exit(direction_id)
        if not exit:
            continue

        if exit.is_door() and exit.is_closed():
            door_exits.append(direction["name"])

        else:
            basic_exits.append(direction["name"])

    line = ""
    line += "{x[{GExits{g:{x %s{x]" % (
        " ".join(basic_exits) if basic_exits else "none"
    )
    line += "   "
    line += "{x[{GDoors{g:{x %s{x]" % (
        " ".join(door_exits) if door_exits else "none"
    )
    self.echo(line)

    players = Characters.query({"online": True, "room_id": room.id})
    for player in players:
        if player == self:
            continue
        self.echo(format_actor(player))

    actors = Actors.query({"room_id": room.id})
    for actor in actors:
        self.echo(format_actor(actor))


def quit_command(self, arguments):
    self.echo("You are quitting.")
    client = self.get_client()
    client.quit()


def me_command(self, arguments):
    message = " ".join(arguments)
    self.gecho(message, emote=True)


class RoomEntity(CollectionEntity):
    def set_room(self, room):
        """Set the Room for the RoomEntity."""
        self.room_id = room.id

    def get_room(self):
        Rooms = self.get_injector("Rooms")
        return Rooms.find(self.room_id)

    def has_flag(self, flag_id):
        """Return whether this Entity has a flag applied or not."""
        return random.randint(0, 10) == 1


class Area(CollectionEntity):
    pass


class Areas(GameCollection):
    WRAPPER_CLASS = Area

    NAME = "areas"
    INDEXES = [
        Index("id", required=True, unique=True),
        Index("name", required=True, unique=True),
    ]


class RoomExit(Entity):
    def __init__(self, data, room, parent_room):
        super(RoomExit, self).__init__(data)
        self._room = room
        self._parent_room = parent_room

    def get_room(self):
        """Return the Room."""
        return self._room

    def get_flags(self):
        """Return list of flags."""
        return self.get("flags", [])

    def has_flag(self, flag_id):
        """Return whether the flag is present."""
        return flag_id in self.get_flags()

    def is_door(self):
        """Return whether exit is a door or not."""
        return self.has_flag("door")

    def is_closed(self):
        """Return whether exit is closed or not."""
        return self.has_flag("closed")

    def is_open(self):
        """Return whether exit is open or not."""
        return not self.is_closed()


# class RoomExits(GameCollection):
#     WRAPPER_CLASS = RoomExit
#
#     NAME = "room_exits"
#     INDEXES = [
#         Index("id", required=True, unique=True),
#         Index("direction_id"),
#         Index("room_id"),
#     ]


class Room(CollectionEntity):
    def get_area(self):
        Areas = self.get_injector("Areas")
        return Areas.find(self.area_id)

    def get_exits(self):
        """Return dict of exits."""
        return self.get("exits", {})

    def get_exit(self, direction_id):
        """Return a RoomExit."""
        Rooms = self.get_injector("Rooms")

        exits = self.get_exits()
        raw_exit = exits.get(direction_id, None)
        if not raw_exit:
            return None

        exit_room = Rooms.get(raw_exit["room_id"])
        return RoomExit(raw_exit, exit_room, self)


class Rooms(GameCollection):
    WRAPPER_CLASS = Room

    NAME = "rooms"
    INDEXES = [
        Index("id", required=True, unique=True),
        Index("name", required=True, unique=True),
        Index("area_id"),
    ]


class Organization(Entity):
    def is_hidden(self):
        return self.hidden is True


# TODO Verify this is the right place?
# TODO Verify this is the right place?
from mud.command_resolver import CommandResolver

COMMAND_RESOLVER = CommandResolver()

for direction_id in DIRECTIONS.keys():
    COMMAND_RESOLVER.add(direction_id, walk_command)

COMMAND_RESOLVER.update({
    "look": look_command,
    "quit": quit_command,
    "me": me_command,
    "swear": swear_command,
    "title": title_command,
    "exception": exception_command,
    "sockets": sockets_command,
    "who": who_command,
    "walk": walk_command,
    "wizlist": wizlist_command,
    "score": score_command,
})

for channel_id in CHANNELS.keys():
    COMMAND_RESOLVER.add(channel_id, channel_command)

for social_id in SOCIALS.keys():
    COMMAND_RESOLVER.add(social_id, social_command)
# TODO Verify this is the right place?
# TODO Verify this is the right place?


class Actor(RoomEntity):
    # TODO move commands and handlers/logic out into their own places
    ONE_CHAR_ALIASES = {
        "'": "say",
        "/": "recall",
        "=": "cgossip",
        "?": "help",
    }

    def matches_keywords(self, keywords):
        return self.keywords.startswith(keywords)

    def get_organization(self, type_id):
        """Return the Organization of a type."""
        from settings import ORGANIZATIONS

        organization_id = self.get_organization_id(type_id)

        if not organization_id:
            return None

        org = ORGANIZATIONS.get(organization_id, None)
        if not org:
            return None

        return Organization(org)

    def get_organization_id(self, type_id):
        """Return the Organization ID that matches the requested type."""
        return self.get_organization_ids().get(type_id, None)

    def get_organization_ids(self):
        """Return the key/value pairs of Organizations."""
        return self.get("organizations", {})

    def can_see(self, target):
        """Return whether this Actor can see target Entity."""
        return True

    def is_visible_to(self, target):
        """Return whether this Actor is visible to the target Entity."""
        return target.can_see(self)

    def format_name_to(self, target):
        """Format the name of an Actor to another target, taking visibility
           into account."""
        if target.can_see(self):
            return self.name
        return "Someone"

    def set_client(self, client):
        self._client = client

    def get_client(self):
        return self._client

    def echo(self, message=""):
        client = self.get_client()
        if client is None:
            return
        client.writeln(message)

    def act_around(self, message, *args, **kwargs):
        self.gecho(message, *args, **kwargs)

    def gecho(self, message, exclude=None):
        exclude = listify(exclude)

        game = self.get_game()
        connections = game.get_connections()
        for conn in connections:
            client = conn.get_client()
            actor = client.get_actor()

            if actor is None:
                continue

            if actor in exclude:
                continue

            actor.echo(message)

    def get_aliases(self):
        return {}

    def get_game(self):
        client = self.get_client()
        if not client:
            return None
        return client.get_game()

    def quit(self):
        client = self.get_client()
        client.quit()

    def handle_command(self, message, ignore_aliases=False):
        message = message.rstrip()

        if not message:
            return

        if not ignore_aliases:
            # Handle a one-character alias prefix
            possible_aliases = "".join(self.ONE_CHAR_ALIASES.keys())
            if message[0] in possible_aliases:
                existing = message
                message = self.ONE_CHAR_ALIASES[existing[0]]
                if existing[1:]:
                    message += " " + existing[1:]

            # Handle player aliases
            aliases = self.get_aliases()
            parts = message.split(" ")
            if parts[0] in aliases:
                parts = aliases[parts[0]].split(" ") + parts[1:]

        command = parts.pop(0).lower()
        arguments = tuple(parts)
        named_arguments = {}

        handlers = COMMAND_RESOLVER.get(command)
        # TODO Add secondary resolution checks: level, access, etc.
        handler = handlers[0] if handlers else None

        # Execute the appropriate code
        if handler is None:
            self.echo("Huh?")
            return

        game = self.get_game()
        try:
            game.inject(
                handler,
                _self=self,
                arguments=arguments,
                message=message,
                **named_arguments
            )
        except Exception as e:
            game.handle_exception(e)
            self.echo("Huh?!  (Code bug detected and reported.)")


class Actors(GameCollection):
    WRAPPER_CLASS = Actor

    NAME = "actors"
    INDEXES = [
        Index("id", required=True, unique=True),
        Index("name", required=True, unique=True),
        Index("room_id"),
    ]


class Character(Actor):
    def matches_keywords(self, keywords):
        return self.name.startswith(keywords)

    def is_immortal(self):
        return self.name == "Kelemvor"

    def generate_password(self, password):
        """Return a SHA256 hashed password with appropriate salting."""
        from settings import PASSWORD_SALT_PREFIX, PASSWORD_SALT_SUFFIX
        salted = PASSWORD_SALT_PREFIX + password + PASSWORD_SALT_SUFFIX
        return hashlib.sha256(salted.encode("utf-8")).hexdigest()

    def password_is(self, password):
        """Return whether the password matches this Character's or not."""
        return self.password == self.generate_password(password)


class Characters(Actors):
    WRAPPER_CLASS = Character

    NAME = "characters"

    INDEXES = Actors.INDEXES + [
        Index("online")
    ]


class ExampleManager(Manager):
    HANDLE_EVENTS = [
        "GAME_TICK",
    ]

    def tick(self, Characters, Rooms, Areas):
        return
        chars = Characters.query({ "room_id": "market_square", "online": True})

        logging.debug("Characters in room market_square:")
        if chars:
            for actors in chars:
                if actors:
                    for char in actors:
                        count = char.get("count", 0)
                        count += 1
                        char.count = count
                        char.save()
                        room = char.get_room()
                        area = room.get_area()
                        logging.debug("* {} - {} - {} - {}".format(
                            char.name,
                            room.name,
                            area.name,
                            char.count
                    ))
        else:
            logging.debug("No characters at market_square")


class Entities(GameCollection):
    pass


class EntityManager(Manager):
    INJECTOR_NAME = None
    DATA_PATH = None

    def tick(self):
        Entities = self.game.get_injector(self.INJECTOR_NAME)

    def start(self):
        Entities = self.game.get_injector(self.INJECTOR_NAME)
        logging.debug("ENTITY MANAGER STARTED")
        for path in glob(self.DATA_PATH + "/*"):
            data = json.loads(open(path).read())
            Entities.save(data)


class CharactersManager(EntityManager):
    INJECTOR_NAME = "Characters"
    DATA_PATH = "data/characters"




class Core(Module):
    MODULE_NAME = "Core"
    VERSION = "0.1.0"

    INJECTORS = {
        "Areas": Areas,
        "Rooms": Rooms,
        "Actors": Actors,
        "Characters": Characters,
    }

    MANAGERS = [
        CharactersManager,
        ExampleManager,
    ]

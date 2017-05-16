#!/usr/bin/env python
"""Import ROT Areas to Undermountain."""

from glob import glob
from settings import ROT_DATA_PATH, DATA_PATH
from utils.hash import get_random_hash
from utils.json import json


areas = {}
rooms = {}
objects = {}
subroutines = {}
actors = {}


def generate_hash():
    return get_random_hash()


def parse_mobile(filename, lines):
    mobile = {
        "id": generate_hash(),
        "description": [],
        "effects": [],
        "raw_extra": [],
    }
    state = "vnum"
    for index, line in enumerate(lines):
        line_ends_string = line.endswith("~")
        cleaned = line.rstrip("~")
        parts = cleaned.split(" ")
        if state == "vnum" and line != "#MOBILES":
            if not line:
                continue
            assert line.startswith("#"), "Line doesn't start with hash: {}" \
                                         .format(line)
            mobile["vnum"] = int(line[1:])
            state = "keywords"

        elif state == "keywords":
            mobile["keywords"] = parts
            state = "name"

        elif state == "name":
            mobile["name"] = cleaned
            state = "room_name"

        elif state == "room_name":
            mobile["room_name"] = cleaned
            state = "something1"

        elif state == "something1":
            if line_ends_string:
                mobile["something1"] = cleaned
            state = "description"

        elif state == "description":
            if line.endswith("~"):
                if cleaned:
                    mobile["description"].append(cleaned)
                state = "race"
            else:
                mobile["description"].append(line)

        elif state == "race":
            mobile["race_id"] = cleaned
            state = "flags1"

        elif state == "flags1":
            mobile["raw_flags1"] = line
            state = "level_and_damage"

        elif state == "level_and_damage":
            mobile["raw_level_and_damage"] = line
            state = "armors"

        elif state == "armors":
            mobile["raw_armors"] = line
            state = "flags2"

        elif state == "flags2":
            mobile["raw_flags2"] = line
            state = "position_and_gender"

        elif state == "position_and_gender":
            mobile["raw_position_and_gender"] = line
            state = "flags3"

        elif state == "flags3":
            mobile["raw_flags3"] = line
            state = "extra"

        elif state == "extra":
            mobile["raw_extra"] = []

        else:
            print("UNHANDLED", line)

    return mobile


def parse_area(filename, lines):
    area = {
        "id": generate_hash(),
        "vnum": filename
    }
    for line in lines:
        if not line:
            continue
        parts = line.split(" ")
        if parts[0] == "Name":
            area["name"] = " ".join(parts[1:]).rstrip("~")
        elif parts[0] == "Builders":
            area["builders"] = parts[1:]
            area["builders"][-1] = area["builders"][-1].rstrip("~")
            if area["builders"][0] == "None":
                area["builders"] = []
        elif parts[0] == "VNUMs":
            area["vnums"] = (int(parts[1]), int(parts[2]))
        elif parts[0] == "Credits":
            area["credits"] = " ".join(parts[1:]).rstrip("~")
        elif parts[0] == "Security":
            area["security"] = int(parts[1])
        elif parts[0] == "Recall":
            area["recall_vnum"] = int(parts[1])
        elif parts[0] == "Faction":
            area["faction_id"] = "" if parts[1] == "~" else \
                parts[1].rstrip("~")
        elif parts[0] == "AQpoints":
            area["area_quest_points"] = int(parts[1])
        elif parts[0] == "Realm":
            area["realm_id"] = int(parts[1])
        elif parts[0] == "Zone":
            area["zone_id"] = int(parts[1])
        else:
            print("UNHANDLED", line)

    areas[area["vnum"]] = area
    return area


def parse_object(filename, lines):
    return None


def parse_room(filename, lines):
    """Convert areafile lines into dict representing Room."""
    state = "vnum"
    room = {
        "id": generate_hash(),
        "area_vnum": filename,
        "description": [],
        "extra_descriptions": {}
    }

    DIRECTION_MAPPINGS = ["north", "east", "south", "west", "up", "down"]

    for index, line in enumerate(lines):
        try:
            if state == "vnum":
                if line.startswith("#"):
                    room["vnum"] = line[1:]
                    state = "name"
                else:
                    raise Exception("Invalid room format")

            elif state == "name":
                room["name"] = line.rstrip("~")
                state = "unknown"

            elif state == "unknown":
                state = "description"

            elif state == "description":
                if line.endswith("~"):
                    state = "flags1"
                else:
                    room["description"].append(line)

            elif state == "flags1":
                print("TODO: Parse room flags1")
                room["raw_flags1"] = line
                state = "flags2"

            elif state == "flags2":
                print("TODO: Parse room flags2")
                room["raw_flags2"] = line
                state = "meta"

            elif state == "meta":
                # Special?
                if line.startswith("S"):
                    print("TODO: Parse 'S' lines")

                # Direction
                elif line.startswith("D"):
                    state = "exit_name"
                    direction_index = int(line[1])
                    direction_id = DIRECTION_MAPPINGS[direction_index]
                    room_exit = {
                        "name": "",
                        "direction_id": direction_id,
                        "description": []
                    }

                # Extra Description
                elif line.startswith("E"):
                    state = "extra_desc_name"
                    extra_desc = {
                        "keywords": "",
                        "description": []
                    }

                # Mana and HP Healing
                elif line.startswith("M"):
                    print("TODO: Properly parse mana/hp heal")
                    room["raw_mana_heal"] = line

                # Mobprogs/Subroutines
                elif line.startswith("X"):
                    print("TODO: Attach mobprogs properly")

                # O? Unknown
                elif line.startswith("O"):
                    print("TODO: Figure out what a room's O meta does", line)

                # Q? Unknown
                elif line.startswith("Q"):
                    print("TODO: Figure out what a room's Q meta does", line)

                # B? Unknown
                elif line.startswith("B"):
                    print("TODO: Figure out what a room's B meta does", line)

                # Z? Unknown
                elif line.startswith("Z"):
                    print("TODO: Figure out what a room's Z meta does", line)

                # Y? Unknown
                elif line.startswith("Y"):
                    print("TODO: Figure out what a room's Y meta does", line)

                # R? Unknown
                elif line.startswith("R"):
                    print("TODO: Figure out what a room's R meta does", line)

                # T? Unknown
                elif line.startswith("T"):
                    print("TODO: Figure out what a room's T meta does", line)

                # V? Unknown
                elif line.startswith("V"):
                    print("TODO: Figure out what a room's V meta does", line)

                # P? Unknown
                elif line.startswith("P"):
                    print("TODO: Figure out what a room's P meta does", line)

                # Clan ownership
                elif line.startswith("C"):
                    room["clan_id"] = line[2:-1]

                # Whitespace is allowed
                elif not line:
                    pass

                # Error
                else:
                    raise Exception("Invalid meta section")

            elif state == "extra_desc_name":
                if line.endswith("~"):
                    state = "extra_desc_desc"
                else:
                    extra_desc["keywords"] += line

            elif state == "extra_desc_desc":
                if line.endswith("~"):
                    keywords = extra_desc["keywords"]
                    room["extra_descriptions"][keywords] = extra_desc
                    state = "meta"
                else:
                    extra_desc["description"].append(line)

            elif state == "exit_name":
                if line.endswith("~"):
                    state = "exit_description"
                else:
                    room_exit["name"] += " " + line

            elif state == "exit_description":
                if line.endswith("~"):
                    state = "exit_flags"
                else:
                    room_exit["description"].append(line)

            elif state == "exit_flags":
                print("TODO: Parse exit flags", line)
                room["raw_flags"] = line
                state = "meta"

            else:
                raise Exception("Unhandled room line")

        except Exception as e:
            print("Exception state:{} file:{} index:{} line:{}".format(
                state, filename, index, line))
            raise

    rooms[room["vnum"]] = room
    return room


def parse_special(filename, lines):
    return None


def parse_reset(filename, lines):
    return None


def parse_shop(filename, lines):
    return None


def parse_mobprog(filename, lines):
    return None


functions = {
    "area": parse_area,
    "mobile": parse_mobile,
    "object": parse_object,
    "room": parse_room,
    "special": parse_special,
    "reset": parse_reset,
    "shop": parse_shop,
    "mobprog": parse_mobprog,
}


class Boop(Exception):
    pass


# Some symbols that improperly trigger bad parsing
ignore_lines_starting_with = [
    '#rhg',
    '#rh',
    '#newthalos',
    '#goddesstatuemoonshae',
    '#questurias',
    '#dernallforestblocker',
    '#invulnerabledruid',
    '#combaturias',
    '#sos',
    '#som',
    '#sea',
    '#norland',
    '#candlekeep',
    '#alaron',
    '#snowdown',
    '#gwynneth',
    '#moray',
    '#norheim',
    '#oman',
    '#archipelago',
    '#flamsterd',
    '#isles',
    '#gardengirl',
    '#passageopener',
    '#passageopener,',
    '#moonshaequest',
]

for path in glob(ROT_DATA_PATH + "/area/*.are"):
    section = None
    content = []
    print("Processing {}..".format(path))
    filename = path.split("/")[-1].split(".")[0]

    if "westbridge" not in path:
        continue

    try:
        for line in open(path, "r"):
            line = line.rstrip("\r\n")
            parts = line.lower().split(' ')
            if line.startswith("#") and parts[0] not in \
                    ignore_lines_starting_with:

                # Some room descriptions contain hash symbols
                if line.startswith("##") or line.startswith("#@"):
                    continue

                if line == "#0":
                    continue

                if section is not None and content:
                    try:
                        function = functions[section]
                        result = function(filename, content)
                    except Exception as e:
                        print("EXCEPTION {} SECTION {}".format(
                            filename, section))
                        for index, line in enumerate(content):
                            print("{}: {}".format(index, line))

                        print("=" * 79)
                        raise

                content = []

                if line == "#AREADATA":
                    section = "area"
                elif line == "#MOBILES":
                    section = "mobile"
                elif line == "#OBJECTS":
                    section = "object"
                elif line == "#ROOMS":
                    section = "room"
                elif line == "#SPECIALS":
                    section = "special"
                elif line == "#RESETS":
                    section = "reset"
                elif line == "#SHOPS":
                    section = "shop"
                elif line == "#MOBPROGS":
                    section = "mobprog"

            if line not in ["#AREADATA", "#ROOMS"]:
                content.append(line)

    except Boop:
        continue

for area in areas.values():
    area["rooms"] = [
        room
        for room in rooms.values()
        if room["area_vnum"] == area["vnum"]
    ]

    output_path = "{}/{}/{}.json".format(DATA_PATH, "areas", area["vnum"])
    with open(output_path, "w") as fh:
        fh.write(json.dumps(area))

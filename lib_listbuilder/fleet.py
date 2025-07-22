import logging
import logging.handlers
import re
import sqlite3

from .utils import unzipall, zipall, scrub_piecename, calc_guid
from .definitions import (
    nomenclature_translation,
    ambiguous_names,
)

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)


class Fleet:
    def __init__(
        self,
        name,
        config,
        faction="",
        points=0,
        mode="",
        fleet_version="",
        description="",
        objectives={},
        ships=[],
        squadrons=[],
        author="",
    ):
        self.name = str(name)
        self.faction = str(faction)
        self.points = int(points)
        self.mode = str(mode)
        self.fleet_version = str(fleet_version)
        self.description = str(description)
        self.objectives = dict(objectives)
        self.ships = list(ships)
        self.squadrons = list(squadrons)
        self.author = str(author)
        self.config = config
        self.conn = self.config.db_path

        # simple piece locations calculations

        self.x = 200
        self.ship_y = 850
        self.upgrade_upper_y = 775

        self.shipcard_to_obj_x_padding = -100
        self.shipcard_to_obj_y_padding = 0
        self.obj_x = self.x + self.shipcard_to_obj_x_padding
        self.obj_y = self.ship_y + self.shipcard_to_obj_y_padding

        self.cmdstack_to_shipcard_x_offset = 90
        self.cmdstack_to_shipcard_y_offset = -10

        self.shipcard_to_shiptoken_x_padding = 173
        self.shipcard_to_shiptoken_y_padding = 0
        self.ship_to_uprgade_padding = 50
        self.upgrade_to_upgrade_x_padding = 145
        self.upgrade_to_upgrade_y_padding = 225
        self.upgrade_to_ship_padding = 195
        self.upgrade_to_squad_padding = 195
        self.upgrade_lower_y = self.upgrade_upper_y + self.upgrade_to_upgrade_y_padding
        self.squad_to_squad_x_padding = 175
        self.squad_to_squad_y_padding = 240
        self.objective_to_objective_x_offset = 25
        self.objective_to_objective_y_offset = 25

        self.squad_y_offset = -120
        self.squad_upper_y = self.ship_y + self.squad_y_offset
        self.squad_lower_y = self.squad_upper_y + self.squad_to_squad_y_padding
        self.squad_row = 1

    def set_name(self, name):
        self.name = str(name)

    def set_faction(self, faction):
        self.faction = str(faction)

    def set_points(self, points):
        if points.isdigit():
            self.points = int(points)
            return
        logging.info("Failed to set points: '{}' cannot be converted to an integer.")
        self.points = int(0)
        return

    def set_mode(self, mode):
        self.mode = str(mode)

    def set_fleet_version(self, fleet_version):
        self.fleet_version = str(fleet_version)

    def set_description(self, description):
        self.description = str(description)

    def set_objectives(self, objectives):
        self.objectives = dict(objectives)

    def add_ship(self, shipclass):
        shipclass = scrub_piecename(shipclass)
        if shipclass in nomenclature_translation:
            sc = nomenclature_translation[shipclass]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Fleet.add_ship().".format(
                    shipclass, sc
                )
            )
            shipclass = sc

        s = Ship(shipclass, self, self.config)
        self.x += self.upgrade_to_ship_padding
        s.set_coords([str(self.x), str(self.ship_y)])
        s.shipcard.set_coords([str(self.x), str(self.ship_y)])
        s.shipcmdstack.set_coords(
            [
                str(self.x + self.cmdstack_to_shipcard_x_offset),
                str(self.ship_y + self.cmdstack_to_shipcard_y_offset),
            ]
        )
        self.x += self.shipcard_to_shiptoken_x_padding
        s.shiptoken.set_coords(
            [str(self.x), str(self.ship_y + self.shipcard_to_shiptoken_y_padding)]
        )
        self.x += self.ship_to_uprgade_padding
        self.u_row = 1

        self.ships.append(s)
        return s

    def remove_ship(self, ship):
        self.ships.remove(ship)

    def add_squadron(self, squadronclass):
        squadronclass = scrub_piecename(squadronclass)
        if squadronclass in nomenclature_translation:
            sc = nomenclature_translation[squadronclass]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Fleet.add_squadron().".format(
                    squadronclass, sc
                )
            )
            squadronclass = sc

        try:
            sq = Squadron(squadronclass, self, self.config)
        except ValueError as err:
            """If the squadron is not found in the database, try scrubbing the word "squadron" and retrying."""
            squadronclass = scrub_piecename(squadronclass.replace("squadron", ""))
            sq = Squadron(squadronclass, self, self.config)
        if self.squad_row % 2:
            self.x += self.squad_to_squad_x_padding
            sq.set_coords([str(self.x), str(self.squad_upper_y)])
            sq.squadroncard.set_coords([str(self.x), str(self.squad_upper_y)])
            sq.squadrontoken.set_coords([str(self.x), str(self.squad_upper_y)])
        else:
            sq.set_coords([str(self.x), str(self.squad_lower_y)])
            sq.squadroncard.set_coords([str(self.x), str(self.squad_lower_y)])
            sq.squadrontoken.set_coords([str(self.x), str(self.squad_lower_y)])
        self.squad_row += 1

        self.squadrons.append(sq)
        return sq

    def remove_squadron(self, squadron):
        self.squadrons.remove(squadron)

    def add_objective(self, category, objectivename):
        category = scrub_piecename(category)
        objectivename = scrub_piecename(objectivename)

        if objectivename in nomenclature_translation:
            ob = nomenclature_translation[objectivename]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Fleet.add_objective()".format(
                    objectivename, ob
                )
            )
            objectivename = ob

        if "custom" in objectivename.lower():
            return False

        obj_categories = ["assault", "defense", "navigation", "campaign", "other"]
        if category.lower() in obj_categories:
            self.objectives[category] = Objective(objectivename, self.config)
        else:
            # except:
            # raise ValueError
            logging.info("{} is not a valid objective type.".format(str(category)))
            logging.info("Valid types are: {}".format(obj_categories))

        self.objectives[category].set_coords([str(self.obj_x), str(self.obj_y)])
        self.obj_x = self.obj_x + self.objective_to_objective_x_offset
        self.obj_y = self.obj_y + self.objective_to_objective_y_offset

    def remove_objective(self, category, objective):
        if category in self.objectives.keys():
            if self.objectives[category] == objective:
                del self.objectives[category]

    def __add__(self, ship):
        self.add_ship(ship)

    def __sub__(self, ship):
        self.remove_ship(ship)


class Piece:
    """A prototype for the other pieces, not to be used on its own"""

    def __init__(self, config):
        self.config = config
        self.conn = config.db_path
        self.guid = calc_guid()
        self.coords = [0, 0]

    def set_coords(self, coords):
        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                r"Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords

    def _fetch_content(self, piecetype, piecename, select_fields="content", like=False):
        """
        Fetches content from the database for a given piece type and name.
        Returns a tuple of fields or raises RuntimeError if not found.
        """
        piecename = scrub_piecename(piecename)
        query = f"select {select_fields} from pieces where piecetype=? and piecename{' like' if like else ''} ?;"
        param = (piecetype, f"%{piecename}%" if like else piecename)
        try:
            with sqlite3.connect(self.conn) as connection:
                result = connection.execute(query, param).fetchall()
            if len(result) == 1:
                return result[0]
            logging.debug(f"Did not find {piecetype} {piecename}")
        except Exception as err:
            logging.exception(err)
            raise


class Ship(Piece):
    """A ship of type str(shipclass) as defined in sqlitedb connection conn."""

    def __init__(self, shipclass, ownfleet, config):
        super().__init__(config)
        self.shipclass = scrub_piecename(str(shipclass))  # "name" in .AFF
        self.content = ""
        self.physicalsize = [
            [0, 0],
            [0, 0],
        ]  # amt of table space for shipcard, stack, and all upgrades
        self.shipcard = ShipCard(self.shipclass, self.config)
        self.shiptoken = self.shipcard.shiptoken
        self.shipcmdstack = self.shipcard.shipcmdstack
        self.upgrades = []

        self.ownfleet = ownfleet

    def set_content(self, content):
        self.content = str(content)

    def set_coords(self, coords):
        self.coords = list(coords)

    def set_shipcard(self, shipcard):
        self.shipcard = shipcard

    def set_shiptoken(self, shiptoken):
        self.shiptoken = shiptoken

    def set_upgrades(self, upgrades):
        self.upgrades = list(upgrades)

    def add_upgrade(self, upgradename):
        upgradename = scrub_piecename(upgradename)
        if upgradename in nomenclature_translation:
            sc = nomenclature_translation[upgradename]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Ship.add_upgrade().".format(
                    upgradename, sc
                )
            )
            upgradename = sc

        u = Upgrade(upgradename, self, self.config)

        if self.ownfleet.u_row % 2:
            self.ownfleet.x += self.ownfleet.u_to_u_x_padding
            u.set_coords([str(self.ownfleet.x), str(self.ownfleet.upgd_upper_y)])
        else:
            u.set_coords([str(self.ownfleet.x), str(self.ownfleet.upgd_lower_y)])
        self.ownfleet.u_row += 1

        self.upgrades.append(u)
        return u

    def remove_upgrade(self, upgrade):
        self.upgrades.remove(upgrade)

    def __add__(self, upgrade):
        self.add_upgrade(upgrade)

    def __sub__(self, upgrade):
        self.remove_upgrade(upgrade)


class ShipCard(Piece):
    """A shipcard of type str(shipname) as defined in sqlitedb connection conn."""

    def __init__(self, shipname, config):
        super().__init__(config)
        self.shipname = scrub_piecename(str(shipname))

        logging.info(
            "Searching for ship {} in {}".format(self.shipname, str(self.conn))
        )

        [(self.content, self.shiptype)] = self._fetch_content(
            self,
            piecetype="shipcard",
            piecename=self.shipname,
            select_fields="content,catchall",
            like=False,
        )

        # try:
        #     with sqlite3.connect(self.conn) as connection:
        #         logging.debug("0")
        #         exact_match = connection.execute(
        #             """select content,catchall
        #             from pieces
        #             where piecetype='shipcard'
        #             and piecename=?;""",
        #             (self.shipname,),
        #         ).fetchall()
        #     if len(exact_match) == 1:
        #         [(self.content, self.shiptype)] = exact_match
        #     if not (hasattr(self, "content") and hasattr(self, "shiptype")):
        #         raise RuntimeError(f"Did not find ship card {self.shipname}")
        # except RuntimeError as err:
        #     logging.debug(err, exc_info=err)
        # except Exception as err:
        #     logging.debug(err, exc_info=err)
        #     raise err

        self.shiptoken = ShipToken(self.shiptype, self.config)

        logging.debug("9")
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")

        logging.debug("10")

        self.command = self.content.split("/placemark;Spawn Command ")[-1][0]
        self.command = "commandstack" + self.command
        self.shipcmdstack = ShipCmdStack(self.command, self.config)

    def set_guid(self, guid):
        self.content = self.content.replace("vlb_GUID", self.guid)

    def set_shiptoken(self, shiptype):
        self.shiptoken = ShipToken(shiptype, self.config)


class ShipToken(Piece):
    """A ship token of type str(shiptype) as defined in sqlitedb connection conn."""

    def __init__(self, shiptype, config):
        super().__init__(config)

        self.shiptype = scrub_piecename(str(shiptype))

        if self.shiptype in nomenclature_translation:
            translated_shiptype = nomenclature_translation[self.shiptype]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.ShipToken.".format(
                    self.shiptype, translated_shiptype
                )
            )
            self.shiptype = translated_shiptype

        logging.info(
            "Searching for ship token {} in {}".format(self.shiptype, str(self.conn))
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='ship' and piecename=?;""",
                    (self.shiptype,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find ship token {self.shiptype}")
        except Exception as err:
            logging.debug(err, exc_info=err)
            raise err

        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")


class ShipCmdStack(Piece):
    """A command stack as defined in sqlitedb connection conn."""

    def __init__(self, cmdstack, config):
        super().__init__(config)

        self.cmdstack = scrub_piecename(str(cmdstack))

        logging.info(
            "Searching for command stack {} in {}".format(self.cmdstack, str(self.conn))
        )
        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='other' and piecename=?;""",
                    (self.cmdstack,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find command stack {self.cmdstack}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.debug(err, exc_info=err)
            raise err

        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")

    def set_guid(self, guid):
        self.content = self.content.replace("vlb_GUID", self.guid)


class Upgrade(Piece):
    """An upgrade of type str(upgradename) as defined in sqlitedb connection conn."""

    def __init__(self, upgradename, ownship, config):
        super().__init__(config)

        self.upgradename = scrub_piecename(str(upgradename))

        logging.info(
            "Searching for upgrade {} in {}".format(self.upgradename, str(self.conn))
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='upgradecard' and piecename=?;""",
                    (self.upgradename,),
                ).fetchall()

            self.content = False
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find upgrade {self.upgradename}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.exception(err)
            raise err

        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")

        self.ownship = ownship


class Squadron(Piece):
    """A squadron of type str(squadronclass) as defined in sqlitedb connection conn."""

    def __init__(self, squadronclass, ownfleet, config):
        super().__init__(config)

        self.squadronclass = scrub_piecename(str(squadronclass))  # "name" in .AFF
        self.conn = self.config.db_path
        self.content = ""
        self.squadroncard = SquadronCard(self.squadronclass, self.conn)
        self.squadrontoken = self.squadroncard.squadrontoken
        self.upgrades = []
        self.ownfleet = ownfleet

    def set_content(self, content):
        self.content = str(content)

    def set_coords(self, coords):
        self.coords = list(coords)

    def set_squadroncard(self, squadroncard):
        self.squadroncard = squadroncard

    def set_squadrontoken(self, squadrontoken):
        self.squadrontoken = squadrontoken


class SquadronCard(Piece):
    """A squadroncard of type str(squadronname) as defined in the sqlite db."""

    def __init__(self, squadronname, config):
        super().__init__(config)

        self.squadronname = scrub_piecename(str(squadronname))
        self.conn = self.config.db_path

        logging.info(
            "Searching for squadron card {} in {}".format(
                self.squadronname, str(self.conn)
            )
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content,catchall 
                    from pieces 
                    where piecetype='squadroncard' and piecename like ?;""",
                    (self.squadronname,),
                ).fetchall()
            if len(exact_match) == 1:
                [(self.content, self.squadrontype)] = exact_match
            else:
                with sqlite3.connect(self.conn) as connection:
                    [(self.content, self.squadrontype)] = connection.execute(
                        """select content,catchall 
                        from pieces 
                        where piecetype='squadroncard' and piecename like ?;""",
                        ("%" + self.squadronname + "%",),
                    ).fetchall()
        except ValueError as err:
            logging.exception(f"Did not find squadron {self.squadronname}")
            raise err
        except Exception as err:
            logging.debug(err, exc_info=err)
            raise err

        self.squadrontoken = SquadronToken(self.squadrontype, self.config)

        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")

    def set_guid(self, guid):
        self.content = self.content.replace("vlb_GUID", self.guid)

    def set_squadrontoken(self, squadrontype):
        self.squadrontoken = SquadronToken(squadrontype, self.conn)


class SquadronToken(Piece):
    """A squadron token of type str(squadrontype) as defined in sqlitedb connection conn."""

    def __init__(self, squadrontype, config):
        super().__init__(config)

        self.squadrontype = scrub_piecename(str(squadrontype))
        self.conn = self.config.db_path
        logging.info(
            "Searching for squadron token {} in {}".format(
                scrub_piecename(squadrontype), str(self.conn)
            )
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='squadron' and piecename=?;""",
                    (self.squadrontype,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find squadron token {self.squadrontype}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.debug(err, exc_info=err)
            raise err

        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")


class Objective(Piece):
    """An objective of type str(objectivename) as defined in sqlitedb connection conn."""

    def __init__(self, objectivename, config):
        super().__init__(config)

        self.objectivename = scrub_piecename(str(objectivename))
        self.conn = self.config.db_path
        logging.info(
            "Searching for objective {} in {}".format(
                self.objectivename, str(self.conn)
            )
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='objective' and piecename=?;""",
                    (self.objectivename,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find objective {self.objectivename}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.debug(err, exc_info=err)
            raise err

        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")

        c = ""
        for line in self.content.split("\t"):
            if line.strip().startswith("piece;;;;"):
                this_line = line.replace("1", "2")
            else:
                this_line = line
            c += this_line + "\t"

        self.content = c

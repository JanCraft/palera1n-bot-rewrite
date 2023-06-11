import mongoengine
import discord
from discord.ext import commands
import os
from typing import Any, Dict, Tuple, Counter
from model import User, Case, Cases
from model.user import User


def get_user(id: int) -> User:
    """Look up the User document of a user, whose ID is given by `id`.
    If the user doesn't have a User document in the database, first create that.

    Parameters
    ----------
    id : int
        The ID of the user we want to look up

    Returns
    -------
    User
        The User document we found from the database.
    """

    user = User.objects(_id=id).first()
    # first we ensure this user has a User document in the database before
    # continuing
    if not user:
        user = User()
        user._id = id
        user.save()
    return user


def leaderboard() -> list:
    return User.objects[0:130].only('_id', 'xp').order_by(
        '-xp', '-_id').select_related()


def leaderboard_rank(xp: int) -> Tuple[int, int]:
    users = User.objects().only('_id', 'xp')
    overall = users().count()
    rank = users(xp__gte=xp).count()
    return (rank, overall)


def inc_points(_id: int, points: int) -> None:
    """Increments the warnpoints by `points` of a user whose ID is given by `_id`.
    If the user doesn't have a User document in the database, first create that.

    Parameters
    ----------
    _id : int
        The user's ID to whom we want to add/remove points
    points : int
        The amount of points to increment the field by, can be negative to remove points
    """

    # first we ensure this user has a User document in the database before
    # continuing
    get_user(_id)
    User.objects(_id=_id).update_one(inc__warn_points=points)


def inc_xp(id: int, xp) -> Tuple[int, int]:
    """Increments user xp.
    """

    get_user(id)
    User.objects(_id=id).update_one(inc__xp=xp)
    u = User.objects(_id=id).first()
    return (u.xp, u.level)


def inc_level(id: int) -> None:
    """Increments user level.
    """

    get_user(id)
    User.objects(_id=id).update_one(inc__level=1)


def get_cases(id: int) -> Cases:
    """Return the Document representing the cases of a user, whose ID is given by `id`
    If the user doesn't have a Cases document in the database, first create that.

    Parameters
    ----------
    id : int
        The user whose cases we want to look up.

    Returns
    -------
    Cases
        [description]
    """

    cases = Cases.objects(_id=id).first()
    # first we ensure this user has a Cases document in the database before
    # continuing
    if cases is None:
        cases = Cases()
        cases._id = id
        cases.save()
    return cases


def add_case(_id: int, case: Case) -> None:
    """Cases holds all the cases for a particular user with id `_id` as an
    EmbeddedDocumentListField. This function appends a given case object to
    this list. If this user doesn't have any previous cases, we first add
    a new Cases document to the database.

    Parameters
    ----------
    _id : int
        ID of the user who we want to add the case to.
    case : Case
        The case we want to add to the user.
    """

    # ensure this user has a cases document before we try to append the new
    # case
    get_cases(_id)
    Cases.objects(_id=_id).update_one(push__cases=case)


def set_warn_kicked(_id: int) -> None:
    """Set the `was_warn_kicked` field in the User object of the user, whose ID is given by `_id`,
    to True. (this happens when a user reaches 400+ points for the first time and is kicked).
    If the user doesn't have a User document in the database, first create that.

    Parameters
    ----------
    _id : int
        The user's ID who we want to set `was_warn_kicked` for.
    """

    # first we ensure this user has a User document in the database before
    # continuing
    get_user(_id)
    User.objects(_id=_id).update_one(set__was_warn_kicked=True)


def rundown(id: int) -> list:
    """Return the 3 most recent cases of a user, whose ID is given by `id`
    If the user doesn't have a Cases document in the database, first create that.

    Parameters
    ----------
    id : int
        The user whose cases we want to look up.

    Returns
    -------
    Cases
        [description]
    """

    cases = Cases.objects(_id=id).first()
    # first we ensure this user has a Cases document in the database before
    # continuing
    if cases is None:
        cases = Cases()
        cases._id = id
        cases.save()
        return []

    cases = cases.cases
    cases = filter(lambda x: x._type != "UNMUTE", cases)
    cases = sorted(cases, key=lambda i: i['date'])
    cases.reverse()
    return cases[0:3]


def retrieve_birthdays(date) -> Any:
    return User.objects(birthday=date)


def transfer_profile(oldmember: int, newmember) -> Tuple[User, int]:
    u = get_user(oldmember)
    u._id = newmember
    u.save()

    u2 = get_user(oldmember)
    u2.xp = 0
    u2.level = 0
    u2.save()

    cases = get_cases(oldmember)
    cases._id = newmember
    cases.save()

    cases2 = get_cases(oldmember)
    cases2.cases = []
    cases2.save()

    return u, len(cases.cases)


def fetch_raids() -> Dict[str, Any]:
    values = {}
    values["Join spam"] = Cases.objects(
        cases__reason__contains="Join spam detected").count()
    values["Join spam over time"] = Cases.objects(
        cases__reason__contains="Join spam over time detected").count()
    values["Raid phrase"] = Cases.objects(
        cases__reason__contains="Raid phrase detected").count()
    values["Ping spam"] = Cases.objects(
        cases__reason__contains="Ping spam").count()
    values["Message spam"] = Cases.objects(
        cases__reason__contains="Message spam").count()

    return values


def fetch_cases_by_mod(_id) -> dict:
    values = {}
    cases = Cases.objects(cases__mod_id=str(_id))
    values["total"] = 0
    cases = list(cases.all())
    final_cases = []
    for target in cases:
        for case in target.cases:
            if str(case.mod_id) == str(_id):
                final_cases.append(case)
                values["total"] += 1

    def get_case_reason(reason: str) -> str:
        string = reason.lower()
        return ''.join(e for e in string if e.isalnum() or e == " ").strip()

    case_reasons = [
        get_case_reason(
            case.reason) for case in final_cases if get_case_reason(
            case.reason) != "temporary mute expired"]
    values["counts"] = sorted(
        Counter(case_reasons).items(), key=lambda item: item[1])
    values["counts"].reverse()
    return values


def fetch_cases_by_keyword(keyword: str) -> dict:
    values = {}
    cases = Cases.objects(cases__reason__contains=keyword)
    cases = list(cases.all())
    values["total"] = 0
    final_cases = []

    for target in cases:
        for case in target.cases:
            if keyword.lower() in case.reason:
                values["total"] += 1
                final_cases.append(case)

    case_mods = [case.mod_tag for case in final_cases]
    values["counts"] = sorted(
        Counter(case_mods).items(), key=lambda item: item[1])
    values["counts"].reverse()
    return values


def set_sticky_roles(_id: int, roles) -> None:
    get_user(_id)
    User.objects(_id=_id).update_one(set__sticky_roles=roles)

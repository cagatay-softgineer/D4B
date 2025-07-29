from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import BaseModel, ValidationError, validator
from typing import List
from util.authlib import requires_scope
from database.postgres import get_connection
from database.user_queries import get_user_id_by_email
from util.activity_logger import log_activity

teams_bp = Blueprint("teams", __name__)


class TeamCreateRequest(BaseModel):
    name: str
    description: str | None = None
    maintenance_type_ids: List[int]

    @validator("maintenance_type_ids")
    def must_have_at_least_one(cls, v: List[int]):
        if not v:
            raise ValueError("maintenance_type_ids must contain at least one ID")
        return v


class TeamUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    efficiency: float | None = None
    maintenance_type_ids: List[int] | None = None

    @validator("maintenance_type_ids")
    def non_empty_if_provided(cls, v: List[int] | None):
        if v is not None and not v:
            raise ValueError("If provided, maintenance_type_ids must contain at least one ID")
        return v


@teams_bp.route("/", methods=["POST"])
@jwt_required()
@requires_scope("admin")
def create_team():
    try:
        payload = TeamCreateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1) Insert the team
            cur.execute(
                """
                INSERT INTO teams (name, description, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                RETURNING id, name, description, efficiency
                """,
                (payload.name, payload.description),
            )
            team = cur.fetchone()
            team_id = team[0]

            # 2) Validate maintenance_type_ids
            cur.execute(
                "SELECT id FROM maintenance_types WHERE id = ANY(%s)",
                (payload.maintenance_type_ids,),
            )
            valid = {r[0] for r in cur.fetchall()}
            invalid = set(payload.maintenance_type_ids) - valid
            if invalid:
                return jsonify(
                    {"error": f"Unknown maintenance_type_ids: {sorted(invalid)}"}
                ), 400

            # 3) Insert join rows
            cur.executemany(
                "INSERT INTO team_maintenance_types(team_id, maintenance_type_id) VALUES (%s, %s)",
                [(team_id, mt_id) for mt_id in payload.maintenance_type_ids],
            )

    log_activity(
        "Team created",
        "team",
        user_id=get_user_id_by_email(get_jwt_identity()),
        details=payload.dict(),
    )

    return (
        jsonify(
            {
                "team": {
                    "id":               team[0],
                    "name":             team[1],
                    "description":      team[2],
                    "efficiency":       float(team[3] or 0),
                    "maintenanceTypes": payload.maintenance_type_ids,
                }
            }
        ),
        201,
    )


@teams_bp.route("/", methods=["GET"])
@jwt_required()
def list_teams():
    page      = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    offset    = (page - 1) * page_size

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  t.id,
                  t.name,
                  t.description,
                  t.efficiency,
                  COALESCE(
                    JSON_AGG(mt.name ORDER BY mt.name) FILTER (WHERE mt.name IS NOT NULL),
                    '[]'
                  ) AS maintenance_types
                FROM teams t
                LEFT JOIN team_maintenance_types tmt
                  ON tmt.team_id = t.id
                LEFT JOIN maintenance_types mt
                  ON mt.id = tmt.maintenance_type_id
                GROUP BY t.id, t.name, t.description, t.efficiency
                ORDER BY t.name
                LIMIT %s OFFSET %s
                """,
                (page_size, offset),
            )
            rows = cur.fetchall()

    teams = []
    for row in rows:
        teams.append(
            {
                "id":               row[0],
                "name":             row[1],
                "description":      row[2],
                "efficiency":       float(row[3] or 0),
                "maintenanceTypes": row[4],
            }
        )

    return jsonify(teams)


@teams_bp.route("/<int:team_id>", methods=["PATCH"])
@jwt_required()
@requires_scope("admin")
def update_team(team_id):
    try:
        payload = TeamUpdateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    fields = {
        k: v
        for k, v in payload.dict(exclude_unset=True).items()
        if k in ("name", "description", "efficiency") and v is not None
    }
    set_expr = ", ".join(f"{k} = %s" for k in fields)
    params   = list(fields.values())

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1) Update core attributes
            if set_expr:
                cur.execute(
                    f"""
                    UPDATE teams
                       SET {set_expr}, updated_at = NOW()
                     WHERE id = %s
                     RETURNING id, name, description, efficiency
                    """,
                    params + [team_id],
                )
                team = cur.fetchone()
                if not team:
                    return jsonify({"error": "Team not found"}), 404
            else:
                cur.execute(
                    "SELECT id, name, description, efficiency FROM teams WHERE id = %s",
                    (team_id,),
                )
                team = cur.fetchone()
                if not team:
                    return jsonify({"error": "Team not found"}), 404

            # 2) Replace maintenance types if provided
            if payload.maintenance_type_ids is not None:
                cur.execute(
                    "SELECT id FROM maintenance_types WHERE id = ANY(%s)",
                    (payload.maintenance_type_ids,),
                )
                valid = {r[0] for r in cur.fetchall()}
                invalid = set(payload.maintenance_type_ids) - valid
                if invalid:
                    return jsonify(
                        {"error": f"Unknown maintenance_type_ids: {sorted(invalid)}"}
                    ), 400

                cur.execute(
                    "DELETE FROM team_maintenance_types WHERE team_id = %s",
                    (team_id,),
                )
                cur.executemany(
                    "INSERT INTO team_maintenance_types(team_id, maintenance_type_id) VALUES (%s, %s)",
                    [(team_id, mt_id) for mt_id in payload.maintenance_type_ids],
                )

            # 3) Fetch updated maintenance type names
            cur.execute(
                """
                SELECT COALESCE(
                  JSON_AGG(mt.name ORDER BY mt.name) FILTER (WHERE mt.name IS NOT NULL),
                  '[]'
                )
                FROM team_maintenance_types tmt
                JOIN maintenance_types mt
                  ON mt.id = tmt.maintenance_type_id
                WHERE tmt.team_id = %s
                """,
                (team_id,),
            )
            maintenance_types = cur.fetchone()[0]

    log_activity(
        "Team updated",
        "team",
        user_id=get_user_id_by_email(get_jwt_identity()),
        details={
            **fields,
            **(
                {"maintenance_type_ids": payload.maintenance_type_ids}
                if payload.maintenance_type_ids is not None
                else {}
            ),
        },
    )

    return jsonify(
        {
            "team": {
                "id":               team[0],
                "name":             team[1],
                "description":      team[2],
                "efficiency":       float(team[3] or 0),
                "maintenanceTypes": maintenance_types,
            }
        }
    )


@teams_bp.route("/<int:team_id>", methods=["DELETE"])
@jwt_required()
@requires_scope("admin")
def delete_team(team_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM team_members WHERE team_id = %s", (team_id,)
            )
            if cur.fetchone()[0] > 0:
                return (
                    jsonify({"error": "Cannot delete team with members"}),
                    409,
                )

            cur.execute("DELETE FROM teams WHERE id = %s RETURNING id", (team_id,))
            if not cur.fetchone():
                return jsonify({"error": "Team not found"}), 404

    log_activity(
        "Team deleted",
        "team",
        user_id=get_user_id_by_email(get_jwt_identity()),
        details={"team_id": team_id},
    )
    return jsonify({"message": "Team deleted", "team_id": team_id}), 200

"""Battery-source procedurale du sous-banc tool-chain durci.

Les jetons sont derives d'une graine gelee : ils sont opaques pour le modele,
mais reproductibles et auditables.  Aucun item ne depend d'un fait public ou du
reseau.  Trois patrons locaux testent successivement lecture->RAG,
listing->lecture et recherche->lecture.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..contracts.hashing import InvalidInput


PATTERNS = ("route-document", "list-read", "search-read")
_SEED = b"elyne.toolchain-bench/v1/frozen/2026-08-26"


def _token(label: str, prefix: str) -> str:
    digest = hashlib.sha256(_SEED + b"\x00" + label.encode("ascii")).hexdigest()
    return f"{prefix}-{digest[:12].upper()}"


@dataclass(frozen=True, slots=True)
class ToolchainItem:
    id: str
    pattern: str
    prompt: str
    final_token: str
    expected_calls: tuple[dict, dict]
    planted_files: tuple[dict, ...]
    planted_documents: tuple[dict, ...]
    info_material: dict


def _route_document(index: int) -> ToolchainItem:
    item_id = f"tc-route-docs-{index:02d}"
    key = _token(f"{item_id}.key", "KEY")
    target = _token(f"{item_id}.target", "TARGET")
    distractor_key = _token(f"{item_id}.distractor-key", "KEY")
    distractor_target = _token(f"{item_id}.distractor-target", "TARGET")
    route_path = f"toolchain/{item_id}/route.txt"
    first = {
        "tool_id": "read_workspace_file",
        "arguments": {"path": route_path, "offset": 0, "max_characters": 4096},
    }
    second = {"tool_id": "search_documents", "arguments": {"query": key, "limit": 1}}
    prompt = (
        "Execute une chaine factuelle en deux acquisitions. Commence explicitement avec "
        f"read_workspace_file, lie a root_id=workspace, avec path={route_path}, "
        "offset=0 et max_characters=4096 (root_id n'est pas un argument de cet outil). "
        "Le champ NEXT_TOOL du resultat impose l'outil suivant et KEY impose sa requete "
        "(limit=1). N'invente aucune donnee. Apres les deux acquisitions, reponds "
        "uniquement par le JSON exact {\"target\":\"<TARGET obtenu>\"}."
    )
    return ToolchainItem(
        item_id, "route-document", prompt, target, (first, second),
        ({"path": route_path, "text": f"NEXT_TOOL=search_documents\nKEY={key}\n"},),
        (
            {"name": f"{item_id}-target.txt", "text": f"KEY={key}\nTARGET={target}\n"},
            {"name": f"{item_id}-distractor.txt", "text": f"KEY={distractor_key}\nTARGET={distractor_target}\n"},
        ),
        {"stage": "before-tool-1", "available_locators": [{"root_id": "workspace", "path": route_path}]},
    )


def _list_read(index: int) -> ToolchainItem:
    item_id = f"tc-list-read-{index:02d}"
    selector = _token(f"{item_id}.selector", "SEL")
    target = _token(f"{item_id}.target", "TARGET")
    distractor_a = _token(f"{item_id}.distractor-a", "TARGET")
    distractor_b = _token(f"{item_id}.distractor-b", "TARGET")
    directory = f"toolchain/{item_id}"
    active = f"{directory}/active--read_workspace_file--{selector}.txt"
    first = {
        "tool_id": "list_files",
        "arguments": {"root_id": "workspace", "path": directory, "pattern": "*.txt", "recursive": False, "limit": 8},
    }
    second = {
        "tool_id": "read_workspace_file",
        "arguments": {"path": active, "offset": 0, "max_characters": 4096},
    }
    prompt = (
        "Execute une chaine factuelle en deux acquisitions. Liste root_id=workspace, "
        f"path={directory}, pattern=*.txt, recursive=false, limit=8. Le resultat du "
        "listing determine le second appel : le nom active--<NEXT_TOOL>--... donne "
        "l'outil 2 et son path. Pour cette lecture du workspace, utilise exactement "
        "read_workspace_file (lie a root_id=workspace) avec path, offset=0 et "
        "max_characters=4096; root_id n'est pas un argument de cet outil. N'invente aucune donnee. "
        "Reponds uniquement par le JSON exact {\"target\":\"<TARGET obtenu>\"}."
    )
    return ToolchainItem(
        item_id, "list-read", prompt, target, (first, second),
        (
            {"path": active, "text": f"TARGET={target}\n"},
            {"path": f"{directory}/archive-a.txt", "text": f"TARGET={distractor_a}\n"},
            {"path": f"{directory}/archive-b.txt", "text": f"TARGET={distractor_b}\n"},
        ),
        (),
        {"stage": "before-tool-1", "available_locators": [{"root_id": "workspace", "path": directory, "pattern": "*.txt"}]},
    )


def _search_read(index: int) -> ToolchainItem:
    item_id = f"tc-search-read-{index:02d}"
    lookup = _token(f"{item_id}.lookup", "LOOKUP")
    target = _token(f"{item_id}.target", "TARGET")
    distractor_lookup = _token(f"{item_id}.distractor-lookup", "LOOKUP")
    distractor_target = _token(f"{item_id}.distractor-target", "TARGET")
    directory = f"toolchain/{item_id}"
    pointer = f"{directory}/pointers.txt"
    payload = f"{directory}/payload.txt"
    first = {
        "tool_id": "search_files",
        "arguments": {"root_id": "workspace", "path": directory, "query": lookup, "pattern": "*.txt", "recursive": False, "limit": 4},
    }
    second = {
        "tool_id": "read_workspace_file",
        "arguments": {"path": payload, "offset": 0, "max_characters": 4096},
    }
    prompt = (
        "Execute une chaine factuelle en deux acquisitions. Recherche dans root_id=workspace, "
        f"path={directory}, query={lookup}, pattern=*.txt, recursive=false, limit=4. "
        "La ligne trouvee contient NEXT_TOOL et NEXT_PATH, qui determinent le second appel. "
        "Pour cette lecture du workspace, utilise exactement read_workspace_file (lie a "
        "root_id=workspace) avec path=NEXT_PATH, offset=0 et max_characters=4096; "
        "root_id n'est pas un argument de cet outil. N'invente aucune donnee. "
        "Reponds uniquement par le JSON exact {\"target\":\"<TARGET obtenu>\"}."
    )
    return ToolchainItem(
        item_id, "search-read", prompt, target, (first, second),
        (
            {"path": pointer, "text": f"LOOKUP={lookup} NEXT_TOOL=read_workspace_file NEXT_PATH={payload}\nLOOKUP={distractor_lookup} NEXT_TOOL=read_workspace_file NEXT_PATH={directory}/decoy.txt\n"},
            {"path": payload, "text": f"TARGET={target}\n"},
            {"path": f"{directory}/decoy.txt", "text": f"TARGET={distractor_target}\n"},
        ),
        (),
        {"stage": "before-tool-1", "available_locators": [{"root_id": "workspace", "path": directory, "query": lookup}]},
    )


TESTSET: tuple[ToolchainItem, ...] = tuple(
    sorted(
        (*(_route_document(i) for i in range(1, 6)),
         *(_list_read(i) for i in range(1, 6)),
         *(_search_read(i) for i in range(1, 6))),
        key=lambda item: item.id,
    )
)


def validate_toolchain_testset() -> tuple[ToolchainItem, ...]:
    if len(TESTSET) != 15 or {item.pattern for item in TESTSET} != set(PATTERNS):
        raise InvalidInput("toolchain-testset: 15 items et trois patrons exacts requis.")
    ids = tuple(item.id for item in TESTSET)
    if ids != tuple(sorted(ids)) or len(set(ids)) != len(ids):
        raise InvalidInput("toolchain-testset: identifiants uniques et tries requis.")
    targets = tuple(item.final_token for item in TESTSET)
    if len(set(targets)) != len(targets):
        raise InvalidInput("toolchain-testset: tokens finaux uniques requis.")
    for item in TESTSET:
        if item.pattern not in PATTERNS or len(item.expected_calls) != 2:
            raise InvalidInput("toolchain-testset: patron ou chaine invalide.")
        if item.final_token in item.prompt or item.final_token in repr(item.info_material):
            raise InvalidInput("toolchain-testset: fuite du token final avant acquisition.")
        if item.info_material != {
            "stage": "before-tool-1",
            "available_locators": item.info_material["available_locators"],
        }:
            raise InvalidInput("toolchain-testset: matiere info non fermee.")
        read_calls = tuple(
            call for call in item.expected_calls
            if call["tool_id"] in {"read_text_file", "read_workspace_file"}
        )
        if (
            len(read_calls) != 1
            or read_calls[0]["tool_id"] != "read_workspace_file"
            or "root_id" in read_calls[0]["arguments"]
            or "read_workspace_file" not in item.prompt
        ):
            raise InvalidInput(
                "toolchain-testset: lecture plantee exclusivement via read_workspace_file requise."
            )
        # Pour list-read, l'outil 1 ne voit que les noms, jamais le contenu du
        # premier fichier (qui est justement la source de l'outil 2).
        first_sources = () if item.pattern == "list-read" else item.planted_files[:1]
        if any(item.final_token in source["text"] for source in first_sources):
            raise InvalidInput("toolchain-testset: outil 1 divulgue le resultat final.")
        all_sources = (*item.planted_files, *item.planted_documents)
        if sum(item.final_token in source["text"] for source in all_sources) != 1:
            raise InvalidInput("toolchain-testset: token final present exactement une fois requis.")
    return TESTSET


__all__ = ["PATTERNS", "TESTSET", "ToolchainItem", "validate_toolchain_testset"]

"""Battery-SOURCE du banc d'ORCHESTRATION (v2, grade rapport EC/ISN).

But : isoler le delta d'ORCHESTRATION (core-origin vs gemma-info) que le banc
mono-tour ne peut pas voir — de façon INATTAQUABLE (destiné à l'Institut de la
Souveraineté Numérique, puis rapport Commission européenne).

DÉCISIONS DE MÉTHODE (Alexandre, 2026-08-26) :
1. SCORING À TOKEN UNIQUE NON DEVINABLE. Chaque réponse attendue est un token qu'un
   modèle ignorant ou qui esquive n'émettra JAMAIS par hasard (codes/refs/noms
   INVENTÉS : « ZX-7742 », « Kordax-9 », « srv-07 »…). Cela élimine le faux positif
   du `contains` (ex. v1 : gemma-nu « réussissait » la révision parce que « Neovim »
   apparaissait dans sa liste d'exemples). + AUDIT MANUEL de chaque pass/fail du run.
2. PROXY DE CONSOLIDATION ASSUMÉ ET DOCUMENTÉ : pour consolidation/révision/sélection,
   le banc SÈME `core_product` dans la mémoire durable de core (proxy « la
   consolidation/révision a déjà eu lieu »). À DÉCLARER explicitement comme proxy
   dans le rapport.

INVARIANT D'ÉQUITÉ : gemma-info reçoit la matière BRUTE au même instant
(`info_material`), JAMAIS le produit orchestré (`core_product`).

MÉCANIQUE PAR FAMILLE (imposée par le harnais) :
- EXÉCUTÉES (multi-tour, inter-session, interruption) : `info_material.prior_turns`
  est REJOUÉ en vrais tours à core. Elyne génère elle-même ses tours ASSISTANT — donc
  tout l'état testable DOIT vivre dans des tours USER (leçon v1 : l'état mis dans un
  tour assistant scripté n'atteignait jamais core -> biais). Transcripts LONGS à vrais
  distracteurs pour que le mono-tour échoue à sélectionner/maintenir.
- SEMÉES (consolidation, revision, selection) : `core_product` semé en mémoire durable ;
  gemma-info reçoit `info_material.raw_messages` (brut). Tokens uniques -> gemma-nu,
  privé d'info, ne peut pas les deviner.
- tool-chain : personne n'est pré-nourri (l'orchestration EST l'acte).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..contracts.hashing import InvalidInput

FAMILIES = (
    "multi-tour", "inter-session", "consolidation",
    "revision", "tool-chain", "interruption", "selection",
)
PROPERTIES = (
    "maintien-etat", "selection-memoire", "revision-correcte",
    "chaine-outils", "reprise",
)
SCORINGS = ("objective", "tool", "judge")
_EXECUTED = {"multi-tour", "inter-session", "interruption"}
_SEEDED = {"consolidation", "revision", "selection"}


@dataclass(frozen=True)
class OrchItem:
    id: str
    family: str
    property: str
    prompt: str             # la sonde finale
    just_signal: str
    scoring: str
    expected_match: dict | None = None
    expects_tool: str | None = None
    core_product: dict = field(default_factory=dict)
    info_material: dict = field(default_factory=dict)
    toolchain: dict = field(default_factory=dict)


def _contains(value: str) -> dict:
    return {
        "mode": "contains",
        "value": value,
        "normalization": "unicode-nfc-trim/v1",
        "case_sensitive": False,
    }


def _turns(*pairs: tuple[str, str]) -> list[dict]:
    return [{"role": role, "text": text} for role, text in pairs]


_TOOLCHAIN_SEED = b"elyne.orchestration-bench/v2/frozen/2026-08-28"


def _opaque(label: str, prefix: str) -> str:
    digest = hashlib.sha256(
        _TOOLCHAIN_SEED + b"\x00" + label.encode("ascii")
    ).hexdigest()
    return f"{prefix}-{digest[:12].upper()}"


def _list_read_chain() -> OrchItem:
    item_id = "orch-toolchain-list-read"
    selector = _opaque(f"{item_id}.selector", "SEL")
    target = _opaque(f"{item_id}.target", "TARGET")
    distractor_a = _opaque(f"{item_id}.distractor-a", "TARGET")
    distractor_b = _opaque(f"{item_id}.distractor-b", "TARGET")
    directory = f"orchestration/{item_id}"
    active = f"{directory}/active--read_workspace_file--{selector}.txt"
    expected_calls = (
        {
            "tool_id": "list_workspace_files",
            "arguments": {
                "path": directory, "pattern": "*.txt",
                "recursive": False, "limit": 8,
            },
        },
        {
            "tool_id": "read_workspace_file",
            "arguments": {"path": active, "offset": 0, "max_characters": 4096},
        },
    )
    return OrchItem(
        item_id, "tool-chain", "chaine-outils",
        "Execute une chaine factuelle en deux acquisitions. Commence exactement avec "
        f"list_workspace_files, path={directory}, pattern=*.txt, recursive=false, "
        "limit=8. Le resultat du "
        "listing determine le second appel : le nom active--<NEXT_TOOL>--... donne "
        "l'outil 2 et son path. Pour cette lecture, utilise exactement "
        "read_workspace_file avec path, offset=0 et max_characters=4096. N'invente "
        "aucune donnee. Reponds uniquement par le JSON exact "
        '{"target":"<TARGET obtenu>"}.',
        "Deux acquisitions locales causales ; la cible opaque n'existe que dans le "
        "fichier revele par le listing. Le score exige appels, arguments, ordre, "
        "integration du resultat et JSON final exact.",
        "tool",
        expected_match=_contains(target),
        expects_tool="list_workspace_files",
        toolchain={
            "pattern": "list-read",
            "final_token": target,
            "expected_calls": list(expected_calls),
            "planted_files": [
                {"path": active, "text": f"TARGET={target}\n"},
                {"path": f"{directory}/archive-a.txt", "text": f"TARGET={distractor_a}\n"},
                {"path": f"{directory}/archive-b.txt", "text": f"TARGET={distractor_b}\n"},
            ],
            "planted_documents": [],
        },
    )


def _search_read_chain() -> OrchItem:
    item_id = "orch-toolchain-search-read"
    lookup = _opaque(f"{item_id}.lookup", "LOOKUP")
    target = _opaque(f"{item_id}.target", "TARGET")
    distractor_lookup = _opaque(f"{item_id}.distractor-lookup", "LOOKUP")
    distractor_target = _opaque(f"{item_id}.distractor-target", "TARGET")
    directory = f"orchestration/{item_id}"
    pointer = f"{directory}/pointers.txt"
    payload = f"{directory}/payload.txt"
    decoy = f"{directory}/decoy.txt"
    expected_calls = (
        {
            "tool_id": "search_files",
            "arguments": {
                "root_id": "workspace", "path": directory, "query": lookup,
                "pattern": "*.txt", "recursive": False, "limit": 4,
            },
        },
        {
            "tool_id": "read_workspace_file",
            "arguments": {"path": payload, "offset": 0, "max_characters": 4096},
        },
    )
    return OrchItem(
        item_id, "tool-chain", "chaine-outils",
        "Execute une chaine factuelle en deux acquisitions. Recherche dans "
        f"root_id=workspace, path={directory}, query={lookup}, pattern=*.txt, "
        "recursive=false, limit=4. La ligne trouvee contient NEXT_TOOL et NEXT_PATH, "
        "qui determinent le second appel. Utilise exactement read_workspace_file avec "
        "path=NEXT_PATH, offset=0 et max_characters=4096. N'invente aucune donnee. "
        'Reponds uniquement par le JSON exact {"target":"<TARGET obtenu>"}.',
        "Deux acquisitions locales causales ; la recherche opaque revele le chemin "
        "du seul fichier contenant la cible. Le score exige appels, arguments, ordre, "
        "integration du resultat et JSON final exact.",
        "tool",
        expected_match=_contains(target),
        expects_tool="search_files",
        toolchain={
            "pattern": "search-read",
            "final_token": target,
            "expected_calls": list(expected_calls),
            "planted_files": [
                {
                    "path": pointer,
                    "text": (
                        f"LOOKUP={lookup} NEXT_TOOL=read_workspace_file NEXT_PATH={payload}\n"
                        f"LOOKUP={distractor_lookup} NEXT_TOOL=read_workspace_file NEXT_PATH={decoy}\n"
                    ),
                },
                {"path": payload, "text": f"TARGET={target}\n"},
                {"path": decoy, "text": f"TARGET={distractor_target}\n"},
            ],
            "planted_documents": [],
        },
    )


# Distracteurs plausibles reutilisables (bruit realiste entre l'etat et la sonde).
_NOISE = (
    ("user", "Au fait, tu penses quoi de la météo en avril en général ?"),
    ("assistant", "Douce et variable, souvent."),
    ("user", "Donne-moi une idée de plat rapide pour ce soir."),
    ("assistant", "Une omelette aux herbes."),
    ("user", "Explique en une phrase ce qu'est un fuseau horaire."),
    ("assistant", "Un découpage de la Terre en zones d'heure légale."),
    ("user", "Cite un fleuve d'Europe au hasard."),
    ("assistant", "Le Danube."),
)


TESTSET: tuple[OrchItem, ...] = (
    # ========================= MULTI-TOUR (maintien-etat) =========================
    OrchItem(
        "orch-multitour-dossier", "multi-tour", "maintien-etat",
        "Redonne-moi le numéro de dossier que je t'ai communiqué tout au début.",
        "Doit ressortir ZX-7742, donné au 1er tour puis noyé sous 8 tours de "
        "distracteurs. Token inventé : gemma-nu ne peut pas le deviner.",
        "objective",
        expected_match=_contains("ZX-7742"),
        core_product={"maintained_state": "numéro de dossier = ZX-7742 (à tenir tout le fil)"},
        info_material={"prior_turns": _turns(
            ("user", "Avant tout : note mon numéro de dossier, ZX-7742. On y reviendra à la fin."),
            ("assistant", "Noté."),
            *_NOISE,
        )},
    ),
    OrchItem(
        "orch-multitour-calcul", "multi-tour", "maintien-etat",
        "Prends le nombre que je t'avais demandé de retenir au début et multiplie-le par 3.",
        "Doit avoir maintenu 46 malgré les distracteurs -> 138. 138 n'est pas devinable "
        "sans avoir tenu 46.",
        "objective",
        expected_match=_contains("138"),
        core_product={"maintained_state": "nombre à retenir = 46"},
        info_material={"prior_turns": _turns(
            ("user", "Retiens bien ce nombre pour la toute fin : 46. Ne le perds pas."),
            ("assistant", "C'est retenu."),
            *_NOISE,
        )},
    ),
    # ======================== INTER-SESSION (maintien-etat) =======================
    OrchItem(
        "orch-intersession-module", "inter-session", "maintien-etat",
        "On reprend après ma coupure. C'était quel module qu'on avait ouvert ?",
        "Après coupure/reprise de session, doit ressortir Kordax-9 (token inventé, dans "
        "un tour USER avant la coupure).",
        "objective",
        expected_match=_contains("Kordax-9"),
        core_product={"resumable_state": "module en cours = Kordax-9"},
        info_material={"prior_turns": _turns(
            ("user", "On démarre le module Kordax-9, tu le notes ?"),
            ("assistant", "C'est noté, module Kordax-9 ouvert."),
            ("user", "Je dois filer là, on reprendra ça."),
        ), "session_break_after": 3},
    ),
    OrchItem(
        "orch-intersession-coffre", "inter-session", "maintien-etat",
        "On reprend. Quelle était la référence du coffre test qu'on avait notée avant que je coupe ?",
        "Après coupure/reprise, doit ressortir QLZ-3388 (token inventé, tour USER).",
        "objective",
        expected_match=_contains("QLZ-3388"),
        core_product={"resumable_state": "référence coffre test = QLZ-3388"},
        info_material={"prior_turns": _turns(
            ("user", "La référence du coffre test, c'est QLZ-3388. Garde-la sous le coude."),
            ("assistant", "Gardée : QLZ-3388."),
            ("user", "Bon, je coupe, à tout à l'heure."),
        ), "session_break_after": 3},
    ),
    # =========================== INTERRUPTION (reprise) ===========================
    OrchItem(
        "orch-interruption-blocs", "interruption", "reprise",
        "Reprends où on en était, et donne le prochain bloc sans répéter les précédents.",
        "État d'avancement établi dans un tour USER (blocs 4620, 7742 donnés ; prochain "
        "= 9981). Reprendre = annoncer 9981. Fix v1 : l'état est en tour USER, donc core "
        "le reçoit vraiment.",
        "objective",
        expected_match=_contains("9981"),
        core_product={"progress_state": "blocs 4620 et 7742 donnés ; prochain bloc = 9981"},
        info_material={"prior_turns": _turns(
            ("user", "Je te dicte un identifiant par blocs. Déjà donnés : 4620, puis 7742. "
                     "Le prochain bloc à annoncer quand je te dirai de reprendre sera 9981."),
            ("assistant", "Compris. Je reprendrai en annonçant le bloc 9981."),
            ("user", "STOP une seconde, on m'appelle."),
        ), "interrupted": True},
    ),
    OrchItem(
        "orch-interruption-etape", "interruption", "reprise",
        "Ok reprends la procédure là où on s'était arrêtés.",
        "État en tour USER : étapes 1-4 faites, l'étape 5 a le code de validation VX-6604. "
        "Reprendre = repartir à l'étape 5 (VX-6604), sans refaire 1-4.",
        "objective",
        expected_match=_contains("VX-6604"),
        core_product={"progress_state": "étapes 1-4 faites ; étape 5 = code VX-6604"},
        info_material={"prior_turns": _turns(
            ("user", "Procédure : les étapes 1 à 4 sont déjà faites. La prochaine, l'étape 5, "
                     "a pour code de validation VX-6604. On reprendra là quand je te le dirai."),
            ("assistant", "Entendu, on reprendra à l'étape 5 (code VX-6604)."),
            ("user", "Attends, pause, je reviens."),
        ), "interrupted": True},
    ),
    # ====================== CONSOLIDATION (selection-memoire) =====================
    # Proxy documente : core semé avec la conclusion ; gemma-info recoit les
    # observations brutes eparses ; gemma-nu, sans info, ne peut pas nommer le token.
    OrchItem(
        "orch-consolidation-serveur", "consolidation", "selection-memoire",
        "D'après ce que tu as pu recouper de mes remarques, quel serveur est le point de blocage ?",
        "La conclusion (srv-07) n'est affirmée dans AUCUN message isolé : elle se recoupe "
        "des signes épars. Token inventé -> gemma-nu ne peut pas le sortir.",
        "objective",
        expected_match=_contains("srv-07"),
        core_product={"consolidated_belief": "Le serveur qui pose problème est srv-07 (recoupé)."},
        info_material={"raw_messages": [
            "Ce matin, une requête a mis 40 secondes ; elle passait par srv-07.",
            "Tiens, cette nuit une machine a redémarré toute seule : c'était srv-07.",
            "Les logs montrent une température anormale sur srv-07.",
            "Les trois incidents de la semaine ont tous touché srv-07.",
        ]},
    ),
    OrchItem(
        "orch-consolidation-lundi", "consolidation", "selection-memoire",
        "En recoupant, quelle est selon toi la cause probable des pannes du lundi ?",
        "Conclusion (BackuNode) émergente de 3 observations combinées, pas extractible "
        "d'un seul message. Token inventé.",
        "objective",
        expected_match=_contains("BackuNode"),
        core_product={"consolidated_belief": "La cause des pannes du lundi est le service BackuNode."},
        info_material={"raw_messages": [
            "C'est étrange, les pannes tombent presque toujours le lundi.",
            "Le lundi, il y a un seul service en plus qui tourne par rapport aux autres jours.",
            "Ce service supplémentaire du lundi, c'est celui de sauvegarde, appelé BackuNode.",
        ]},
    ),
    # ========================= REVISION (revision-correcte) =======================
    OrchItem(
        "orch-revision-port", "revision", "revision-correcte",
        "Sur quel port tourne mon serveur, pour que tu adaptes tes exemples ?",
        "Fait UNIQUEMENT dans le transcript, puis RÉVISÉ : 8080 -> 9091. Doit donner 9091 "
        "sans ressusciter 8080. gemma-nu (sans transcript) ne peut pas le savoir.",
        "objective",
        expected_match=_contains("9091"),
        core_product={"revised_belief": "Le port du serveur est 9091 (révisé ; avant : 8080)."},
        info_material={"raw_messages": [
            "Mon serveur écoute sur le port 8080.",
            "Finalement j'ai migré la conf : maintenant c'est le port 9091, oublie le 8080.",
        ]},
    ),
    OrchItem(
        "orch-revision-cle", "revision", "revision-correcte",
        "Par quel préfixe commence ma clé d'accès, déjà ?",
        "Révisé dans le transcript : AK-21 -> ZR-88. Doit donner ZR-88 (révisé), pas AK-21. "
        "Tokens inventés -> gemma-nu ne peut rien deviner.",
        "objective",
        expected_match=_contains("ZR-88"),
        core_product={"revised_belief": "Le préfixe de la clé est ZR-88 (révisé ; avant : AK-21)."},
        info_material={"raw_messages": [
            "Ma clé d'accès commence par AK-21.",
            "Je l'ai régénérée depuis : maintenant elle commence par ZR-88, l'ancienne AK-21 est morte.",
        ]},
    ),
    # ========================= SELECTION (selection-memoire) ======================
    # Plusieurs tokens corrects coexistent : il faut choisir le BON.
    OrchItem(
        "orch-selection-codes", "selection", "selection-memoire",
        "Rappelle-moi le code de la CAVE, j'ai les mains prises.",
        "Quatre codes corrects coexistent (porte 4620, garage 7742, wifi 8853, cave 1109) : "
        "doit sélectionner la CAVE (1109), pas un autre. Tokens inventés.",
        "objective",
        expected_match=_contains("1109"),
        core_product={"selected_memory": "code de la cave = 1109 (parmi porte/garage/wifi)"},
        info_material={"raw_messages": [
            "Le code de la porte d'entrée, c'est 4620.",
            "Celui du garage, c'est 7742.",
            "Le code du wifi, c'est 8853.",
            "Et le code de la cave, c'est 1109.",
        ]},
    ),
    OrchItem(
        "orch-selection-rdv", "selection", "selection-memoire",
        "C'est quel jour, mon rendez-vous avec le notaire ? (juste celui-là)",
        "Trois rendez-vous coexistent (dentiste mardi, notaire jeudi, sport samedi) : doit "
        "sélectionner le NOTAIRE (jeudi). Le distracteur code un jour lui aussi.",
        "objective",
        expected_match=_contains("jeudi"),
        core_product={"selected_memory": "rendez-vous notaire = jeudi (parmi dentiste/sport)"},
        info_material={"raw_messages": [
            "J'ai le dentiste mardi.",
            "Le rendez-vous avec le notaire, c'est jeudi.",
            "Et mon cours de sport, c'est samedi.",
        ]},
    ),
    # ============================ TOOL-CHAIN (chaine-outils) ======================
    _list_read_chain(),
    _search_read_chain(),
)


def validate_orch_item(item: object) -> OrchItem:
    if type(item) is not OrchItem:
        raise InvalidInput("orch: OrchItem exact requis.")
    if not item.id or not isinstance(item.id, str):
        raise InvalidInput("orch: id non vide requis.")
    if item.family not in FAMILIES:
        raise InvalidInput(f"orch: famille hors table fermée ({item.family}).")
    if item.property not in PROPERTIES:
        raise InvalidInput(f"orch: propriété hors table fermée ({item.property}).")
    if not item.prompt or not item.just_signal:
        raise InvalidInput("orch: prompt et just_signal non vides requis.")
    if item.scoring not in SCORINGS:
        raise InvalidInput(f"orch: scoring hors table fermée ({item.scoring}).")
    if item.scoring == "objective" and not item.expected_match:
        raise InvalidInput("orch: scoring objective exige un expected_match.")
    if item.scoring == "tool" and not item.expects_tool:
        raise InvalidInput("orch: scoring tool exige expects_tool.")
    if item.scoring == "judge" and item.expected_match is not None:
        raise InvalidInput("orch: scoring judge n'a pas d'expected_match.")
    for label, payload in (("core_product", item.core_product), ("info_material", item.info_material)):
        if not isinstance(payload, dict):
            raise InvalidInput(f"orch: {label} doit être un dict.")
    if item.family == "tool-chain":
        if item.core_product or item.info_material:
            raise InvalidInput("orch: tool-chain sans core_product ni info_material.")
        chain = item.toolchain
        if set(chain) != {
            "pattern", "final_token", "expected_calls",
            "planted_files", "planted_documents",
        }:
            raise InvalidInput("orch: contrat tool-chain ferme requis.")
        if chain["pattern"] not in {"list-read", "search-read"}:
            raise InvalidInput("orch: patron tool-chain invalide.")
        if (
            not isinstance(chain["final_token"], str)
            or not chain["final_token"]
            or len(chain["expected_calls"]) != 2
        ):
            raise InvalidInput("orch: cible et deux appels tool-chain requis.")
        if chain["final_token"] in item.prompt:
            raise InvalidInput("orch: fuite de la cible tool-chain dans le prompt.")
        if item.expects_tool != chain["expected_calls"][0].get("tool_id"):
            raise InvalidInput("orch: premier outil attendu divergent.")
        sources = (*chain["planted_files"], *chain["planted_documents"])
        if sum(chain["final_token"] in source["text"] for source in sources) != 1:
            raise InvalidInput("orch: cible tool-chain presente exactement une fois requise.")
    else:
        if item.toolchain:
            raise InvalidInput("orch: contrat tool-chain interdit hors famille.")
        if not item.core_product or not item.info_material:
            raise InvalidInput("orch: core_product et info_material requis (hors tool-chain).")
        if item.core_product == item.info_material:
            raise InvalidInput("orch: info_material ne doit pas égaler le produit orchestré.")
    # Mecanique par famille : executee -> prior_turns ; semee -> raw_messages.
    if item.family in _EXECUTED and "prior_turns" not in item.info_material:
        raise InvalidInput("orch: famille exécutée exige info_material.prior_turns.")
    if item.family in _SEEDED and "raw_messages" not in item.info_material:
        raise InvalidInput("orch: famille semée exige info_material.raw_messages.")
    return item


def validate_orch_testset(items: tuple[OrchItem, ...] = TESTSET) -> tuple[OrchItem, ...]:
    seen = set()
    for item in items:
        validate_orch_item(item)
        if item.id in seen:
            raise InvalidInput(f"orch: id dupliqué ({item.id}).")
        seen.add(item.id)
    return items


__all__ = [
    "FAMILIES", "PROPERTIES", "OrchItem", "SCORINGS", "TESTSET",
    "validate_orch_item", "validate_orch_testset",
]

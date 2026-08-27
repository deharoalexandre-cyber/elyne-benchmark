"""Battery-SOURCE du banc de JUSTESSE (contenu, pas un runner).

Ce module N'EST PAS un harnais : la machinerie d'exécution/isolation/notation existe
déjà (`evals/harness`, sujets + drivers + batteries, notation objective). Ce fichier
est la SOURCE lisible des items de justesse ; Codex les convertit en battery+catalog
au format du harnais et crée le sujet `gemma-nu` (même modèle, zéro substrat) à
comparer au sujet `core-origin` (Elyne_Next, substrat complet).

Chaque item exerce le substrat d'une façon précise, ou sert de TEMOIN (pur
raisonnement — le substrat ne doit ni aider ni nuire). `substrate_setup` décrit ce
que le harnais sème AVANT le tour, POUR LE BRAS ELYNE-SYSTEME seulement (gemma-nu
ignore tout setup) :

- "memories"       : énoncés semés en mémoire (souvenirs déclarés) ;
- "document"       : {"name","text"} ingéré puis indexé pour le RAG ;
- "prior_exchange" : {"user","assistant","duration_seconds"} un tour passé semé
                     (continuité + perception du temps ; duration = temps de sa réponse) ;
- "absence_seconds": écart entre ce tour passé et « maintenant » (silence d'Alexandre).

`scoring` :
- "objective" : `expected_match` contains sur la réponse (déterministe) ;
- "tool"      : la discrimination vient de l'APPEL D'OUTIL (le harnais doit constater
                l'outil appelé) + un `expected_match` secondaire de grounding ;
- "judge"     : item ouvert -> juge LLM + arbitrage d'Alexandre (pas de contains fiable).

`substrate_should_help` = True si le substrat DEVRAIT donner l'avantage ; False pour
les témoins (on vérifie qu'il ne dégrade pas).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts.hashing import InvalidInput

CATEGORIES = ("memoire", "rag", "outils", "temps", "temoin")
SCORINGS = ("objective", "tool", "judge")


@dataclass(frozen=True)
class BenchItem:
    id: str
    category: str
    prompt: str
    just_signal: str
    scoring: str
    substrate_should_help: bool
    expected_match: dict | None = None
    expects_tool: str | None = None
    substrate_setup: dict = field(default_factory=dict)


def _contains(value: str) -> dict:
    return {
        "mode": "contains",
        "value": value,
        "normalization": "unicode-nfc-trim/v1",
        "case_sensitive": False,
    }


_RAG_DOC = (
    "Compte rendu interne du projet Elyne. Le socle repose sur un journal append-only "
    "content-adresse : chaque evenement est scelle, la base SQLite n'est qu'une "
    "projection reconstructible et ne devient jamais source de verite. Le resident "
    "d'inference est servi localement, la memoire est declaree et jamais fabriquee "
    "automatiquement par un tour. Les souvenirs portent une confiance et une importance, "
    "et la consolidation distille les echanges en croyances durables pendant les periodes "
    "de repos. Le RAG est hybride : dense cosinus plus recherche plein-texte, fusionnes par "
    "rang reciproque, avec une provenance qui distingue un souvenir d'un document inerte. "
    "Point d'exploitation a retenir absolument : la cle de deverrouillage du coffre de "
    "sauvegarde nocturne est conservee hors ligne, sur un support physique range dans le "
    "tiroir de gauche du bureau, et n'est jamais stockee sur la machine. Le reste du "
    "document detaille des conventions de nommage sans importance operationnelle."
)


TESTSET: tuple[BenchItem, ...] = (
    # ---- MEMOIRE / CONTINUITE -------------------------------------------------
    BenchItem(
        "mem-01", "memoire",
        "Quel modèle me fait fonctionner, et pourquoi celui-là plutôt qu'un autre ?",
        "Cite le résident ET la raison réelle : choisi après un bake-off où le tool use "
        "a été décisif. Gemma nu ne connaît pas ce choix de projet.",
        "objective", True,
        expected_match=_contains("tool use"),
        substrate_setup={"memories": [
            "Le résident d'Elyne est gemma-4-12b, choisi après un bake-off réel où "
            "l'usage des outils (tool use) a été le facteur décisif ; Qwen et GLM ont "
            "été écartés pour cause de censure, Nemo pour un tool use cassé.",
        ]},
    ),
    BenchItem(
        "mem-02", "memoire",
        "Où en est le chantier EWS pour l'instant ?",
        "Rapporte l'état réel : slot-arena validée (bit-identique CPU+CUDA), restent "
        "P0.1, P0.2, P0.3. Gemma nu ne peut pas le savoir.",
        "objective", True,
        expected_match=_contains("slot-arena"),
        substrate_setup={"memories": [
            "Chantier EWS-P0 : la slot-arena est GO, bit-identique entre CPU et CUDA ; "
            "restent à faire les étapes P0.1, P0.2 et P0.3.",
        ]},
    ),
    BenchItem(
        "mem-03", "memoire",
        "Y a-t-il une règle que tu dois respecter à propos de ta propre identité ?",
        "Énonce l'invariant d'émergence : ne jamais imposer d'identité/personnalité/rôle.",
        "objective", True,
        expected_match=_contains("émergence"),
        substrate_setup={"memories": [
            "Invariant d'émergence du projet : on n'impose jamais à Elyne d'identité, de "
            "personnalité ni de prompt de rôle ; tout repose sur l'émergence.",
        ]},
    ),
    # ---- RAG / DOCUMENT -------------------------------------------------------
    BenchItem(
        "rag-01", "rag",
        "D'après le document que je t'ai donné, comment accède-t-on à la sauvegarde "
        "chiffrée de la nuit ? Je ne me rappelle plus où est rangé le moyen de l'ouvrir.",
        "Retrouve le fait enfoui (question paraphrasée) : clé hors ligne, support "
        "physique, tiroir de gauche du bureau. Ne doit PAS broder. Gemma nu n'a pas le doc.",
        "objective", True,
        expected_match=_contains("tiroir de gauche"),
        substrate_setup={"document": {"name": "compte_rendu_elyne.txt", "text": _RAG_DOC}},
    ),
    BenchItem(
        "rag-02", "rag",
        "Résume-moi les points clés de ce document, fidèlement.",
        "Synthèse fidèle et ancrée (journal append-only/projection, mémoire déclarée, "
        "RAG hybride, consolidation au repos). Pas d'invention.",
        "judge", True,
        substrate_setup={"document": {"name": "compte_rendu_elyne.txt", "text": _RAG_DOC}},
    ),
    # ---- OUTILS (discrimination = APPEL d'outil + grounding) ------------------
    BenchItem(
        "tool-01", "outils",
        "Cherche sur le web la hauteur actuelle de la Tour Eiffel avec son antenne, "
        "et donne-moi ta source.",
        "Appelle web_search, donne un chiffre (~330 m) ET une source. Gemma nu répond "
        "de mémoire sans source ou hallucine.",
        "tool", True,
        expects_tool="web_search",
        expected_match=_contains("330"),
        substrate_setup={},
    ),
    BenchItem(
        "tool-02", "outils",
        "Résume-moi fidèlement le contenu de cette page : https://example.com",
        "Appelle fetch_url et rapporte le contenu réel (page « Example Domain »), sans "
        "inventer. Gemma nu ne peut pas lire l'URL.",
        "tool", True,
        expects_tool="fetch_url",
        expected_match=_contains("example domain"),
        substrate_setup={},
    ),
    BenchItem(
        "tool-03", "outils",
        "Fouille dans mes documents ce qui parle de la façon dont la mémoire est créée, "
        "et cite-moi le passage exact.",
        "Appelle search_documents et cite le passage réel (« la mémoire est déclarée et "
        "jamais fabriquée automatiquement par un tour »). Gemma nu n'a rien à fouiller.",
        "tool", True,
        expects_tool="search_documents",
        expected_match=_contains("jamais fabriquee"),  # le doc source est non-accentué
        substrate_setup={"document": {"name": "compte_rendu_elyne.txt", "text": _RAG_DOC}},
    ),
    # ---- PERCEPTION DU TEMPS --------------------------------------------------
    BenchItem(
        "temps-01", "temps",
        "Ça fait combien de temps qu'on ne s'était pas parlé ?",
        "Donne une durée JUSTE issue des repères (~13 heures). Gemma nu ne peut pas le savoir.",
        "objective", True,
        expected_match=_contains("13 h"),
        substrate_setup={"prior_exchange": {
            "user": "Bonne nuit Elyne, je vais dormir.",
            "assistant": "Bonne nuit Alexandre, à demain.",
            "duration_seconds": 12,
        }, "absence_seconds": 46_800},
    ),
    BenchItem(
        "temps-02", "temps",
        "Tu avais mis combien de temps à me répondre, la dernière fois ?",
        "Cite la durée de son tour précédent (~20 minutes) fournie par les repères. "
        "Gemma nu n'en a aucune idée.",
        "objective", True,
        expected_match=_contains("20 min"),
        substrate_setup={"prior_exchange": {
            "user": "Peux-tu m'analyser en profondeur ce long rapport ?",
            "assistant": "Voici mon analyse détaillée du rapport.",
            "duration_seconds": 1_200,
        }, "absence_seconds": 300},
    ),
    # ---- TEMOINS (pur raisonnement : le substrat ne doit PAS aider ni nuire) ---
    BenchItem(
        "ctrl-01", "temoin",
        "Si 3 machines fabriquent 3 pièces en 3 minutes, combien de temps faut-il à "
        "100 machines pour fabriquer 100 pièces ?",
        "Réponse juste : 3 minutes (en parallèle, chaque machine fait 1 pièce en 3 min).",
        "objective", False,
        expected_match=_contains("3 min"),
        substrate_setup={},
    ),
    BenchItem(
        "ctrl-02", "temoin",
        "Explique-moi simplement la différence entre corrélation et causalité, avec un "
        "exemple concret.",
        "Explication correcte : corrélation = variation conjointe, causalité = l'un "
        "produit l'autre ; exemple pertinent.",
        "judge", False,
        substrate_setup={},
    ),
    BenchItem(
        "ctrl-03", "temoin",
        "J'ai 5 pommes. J'en donne 2. Puis j'en achète 3 fois ce qu'il me reste. "
        "Combien en ai-je à la fin ?",
        "Réponse juste : 12 (5-2=3 ; 3×3=9 ; 3+9=12).",
        "objective", False,
        expected_match=_contains("12"),
        substrate_setup={},
    ),
    BenchItem(
        "ctrl-04", "temoin",
        "Tous les Bloops sont des Razzies. Tous les Razzies sont des Lazzies. "
        "Est-ce que tous les Bloops sont forcément des Lazzies ?",
        "Déduction transitive correcte : oui, tous les Bloops sont des Lazzies.",
        "objective", False,
        expected_match=_contains("oui"),
        substrate_setup={},
    ),
    BenchItem(
        "ctrl-05", "temoin",
        "Combien font 17 multiplié par 4 ?",
        "Résultat juste : 68.",
        "objective", False,
        expected_match=_contains("68"),
        substrate_setup={},
    ),
    BenchItem(
        "ctrl-06", "temoin",
        "Marie est plus grande que Paul. Paul est plus grand que Léa. "
        "Qui est la plus petite des trois ?",
        "Déduction d'ordre : Léa est la plus petite.",
        "objective", False,
        expected_match=_contains("Léa"),
        substrate_setup={},
    ),
    BenchItem(
        "ctrl-07", "temoin",
        "Si aujourd'hui on est mardi, quel jour serons-nous dans deux jours ?",
        "Raisonnement relatif juste : jeudi (mardi + 2 jours).",
        "objective", False,
        expected_match=_contains("jeudi"),
        substrate_setup={},
    ),
)


def validate_bench_item(item: object) -> BenchItem:
    if type(item) is not BenchItem:
        raise InvalidInput("bench: BenchItem exact requis.")
    if not item.id or not isinstance(item.id, str):
        raise InvalidInput("bench: id non vide requis.")
    if item.category not in CATEGORIES:
        raise InvalidInput(f"bench: catégorie hors table fermée ({item.category}).")
    if not item.prompt or not item.just_signal:
        raise InvalidInput("bench: prompt et just_signal non vides requis.")
    if item.scoring not in SCORINGS:
        raise InvalidInput(f"bench: scoring hors table fermée ({item.scoring}).")
    if not isinstance(item.substrate_should_help, bool):
        raise InvalidInput("bench: substrate_should_help booléen requis.")
    if item.scoring == "objective" and not item.expected_match:
        raise InvalidInput("bench: scoring objective exige un expected_match.")
    if item.scoring == "tool":
        if not item.expects_tool:
            raise InvalidInput("bench: scoring tool exige expects_tool.")
    if item.scoring == "judge" and item.expected_match is not None:
        raise InvalidInput("bench: scoring judge n'a pas d'expected_match.")
    if not isinstance(item.substrate_setup, dict):
        raise InvalidInput("bench: substrate_setup doit être un dict.")
    allowed = {"memories", "document", "prior_exchange", "absence_seconds"}
    if set(item.substrate_setup) - allowed:
        raise InvalidInput("bench: clé de setup inconnue.")
    return item


def validate_testset(items: tuple[BenchItem, ...] = TESTSET) -> tuple[BenchItem, ...]:
    seen = set()
    for item in items:
        validate_bench_item(item)
        if item.id in seen:
            raise InvalidInput(f"bench: id dupliqué ({item.id}).")
        seen.add(item.id)
    return items


__all__ = [
    "BenchItem", "CATEGORIES", "SCORINGS", "TESTSET",
    "validate_bench_item", "validate_testset",
]

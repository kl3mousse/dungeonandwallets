#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                       DONJON & WALLETS (D&W).                              ║
║                  Lance les Dés. Scelle ta Phrase Secrète.                  ║
╚═══════════════════════════════════════════════════════════════════════════╝

Application terminal thématique RPG pour générer des phrases mnémoniques BIP39.

UTILISATION :
    python dw_app.py

PRÉREQUIS :
    pip install textual rich

MODES :
    🎲 Rituel des Dés (Recommandé) - Génère l'entropie à partir de lancers D20 + d100
    ✨ Rituel Aléatoire - Utilise le générateur cryptographique du système
    🧪 Rituel Hex - Fournis ta propre entropie hex de 32 caractères

SÉCURITÉ :
    - Exécute HORS LIGNE pour une sécurité maximale
    - La phrase mnémonique n'est jamais enregistrée sauf export explicite
    - L'affichage de la phrase nécessite une confirmation explicite
    - Aucune opération presse-papiers par défaut

Auteur : kl3mousse
Licence : MIT
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button, Static, Input, Label, Header, Footer, 
    ProgressBar, RichLog, Placeholder
)
from textual.screen import Screen
from textual.binding import Binding
from textual.validation import Validator, ValidationResult
from textual import events
from textual.reactive import reactive
from textual.message import Message

from rich.panel import Panel
from rich.text import Text
from rich.console import Console, Group
from rich.table import Table
from rich.align import Align
from rich.style import Style

# Optional QR code support
try:
    import qrcode
    from qrcode.console_scripts import main as qr_main
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# Import core module
from core import (
    load_wordlist,
    entropy_to_mnemonic,
    random_entropy,
    hex_to_entropy,
    validate_hex_input,
    DiceEntropyCollector,
    derive_wallet_info,
    mask_mnemonic,
    WalletInfo,
)

# ============================================================================
# CONSTANTS & ASCII ART
# ============================================================================

WORDLIST_PATH = Path(__file__).parent / "english.txt"

ASCII_BANNER = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║    ██████╗  ██╗   ██╗ ███╗   ██╗  ██████╗  ███████╗  ██████╗  ███╗   ██╗      ║
║    ██╔══██╗ ██║   ██║ ████╗  ██║ ██╔════╝  ██╔════╝ ██╔═══██╗ ████╗  ██║      ║
║    ██║  ██║ ██║   ██║ ██╔██╗ ██║ ██║  ███╗ █████╗   ██║   ██║ ██╔██╗ ██║      ║
║    ██║  ██║ ██║   ██║ ██║╚██╗██║ ██║   ██║ ██╔══╝   ██║   ██║ ██║╚██╗██║      ║
║    ██████╔╝ ╚██████╔╝ ██║ ╚████║ ╚██████╔╝ ███████╗ ╚██████╔╝ ██║ ╚████║      ║
║    ╚═════╝   ╚═════╝  ╚═╝  ╚═══╝  ╚═════╝  ╚══════╝  ╚═════╝  ╚═╝  ╚═══╝      ║
║                                                                               ║
║                              ⚔️ ⚔️   AND  ⚔️ ⚔️                                   ║
║                                                                               ║
║      ██╗    ██╗  █████╗  ██╗      ██╗      ███████╗ ████████╗ ███████╗        ║
║      ██║    ██║ ██╔══██╗ ██║      ██║      ██╔════╝ ╚══██╔══╝ ██╔════╝        ║
║      ██║ █╗ ██║ ███████║ ██║      ██║      █████╗      ██║    ███████╗        ║
║      ██║███╗██║ ██╔══██║ ██║      ██║      ██╔══╝      ██║    ╚════██║        ║
║      ╚███╔███╔╝ ██║  ██║ ███████╗ ███████╗ ███████╗    ██║    ███████║        ║
║       ╚══╝╚══╝  ╚═╝  ╚═╝ ╚══════╝ ╚══════╝ ╚══════╝    ╚═╝    ╚══════╝        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

ASCII_BANNER_SIMPLE = """
╭──────────────────────────────────────────────────────────╮
│    ⚔️   D O N J O N   &   P O R T E F E U I L L E S   ⚔️  │
│        "Lance les dés. Scelle ton destin."               │
╰──────────────────────────────────────────────────────────╯
"""

DICE_INSTRUCTIONS = """[bold cyan]🎲 Le Rituel Sacré :[/bold cyan] Lance D20+d100 → Les Dieux calculent N = (D20-1)×100 + d100 → Les jets < 1792 sont bénis ! Collecte 16 jets sacrés."""

WHY_DICE_TEXT = """
[italic]"Écoute-moi, brave aventurier..."[/italic]

Les dés physiques sont des artefacts du VRAI chaos —
hors de portée de toute sorcellerie numérique.

✦ Aucune magie noire ne peut prédire leur chute
✦ Aucune porte dérobée dans les lois de la physique  
✦ Ton entropie vient de l'univers lui-même
✦ Protection maximale contre les forces invisibles

[dim]"Dans le donjon de la cryptographie, tu forges ton propre destin."[/dim]
"""

SECURITY_WARNING = """
⚔️  ENTENDS CET AVERTISSEMENT, ÂME COURAGEUSE !  ⚔️

Ces mots sacrés sont la CLÉ MAÎTRESSE de ton trésor.
Garde-les comme un dragon garde son or !

🚫 N'autorise aucun œil espion à voir ces mots
🚫 Ne capture jamais sur cristal (capture d'écran)
🚫 N'inscris jamais sur tablettes des nuages (cloud)
🚫 Ne les révèle à aucun être, numérique ou mortel
🚫 N'envoie jamais par corbeau messager ou feu de signal

✅ Inscris sur parchemin physique uniquement
✅ Cache en plusieurs coffres fortifiés
✅ Envisage des coffres ignifugés/étanches
✅ Ne confie l'emplacement qu'à tes alliés jurés
"""


# ============================================================================
# CUSTOM VALIDATORS
# ============================================================================

class D20Validator(Validator):
    """Validate D20 roll input (1-20)"""
    
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure("Entre le résultat du D20 (1-20)")
        try:
            n = int(value)
            if 1 <= n <= 20:
                return self.success()
            return self.failure("Le D20 doit être entre 1 et 20")
        except ValueError:
            return self.failure("Entre un nombre")


class D100Validator(Validator):
    """Validate d100 roll input (0-99)"""
    
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure("Entre le résultat du d100 (0-99)")
        try:
            n = int(value)
            if 0 <= n <= 99:
                return self.success()
            return self.failure("Le d100 doit être entre 0 et 99")
        except ValueError:
            return self.failure("Entre un nombre")


class HexValidator(Validator):
    """Validate hex entropy input"""
    
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure("Entre 32 caractères hex")
        is_valid, error = validate_hex_input(value, 16)
        if is_valid:
            return self.success()
        return self.failure(error)


# ============================================================================
# TITLE SCREEN
# ============================================================================

class TitleScreen(Screen):
    """Title/Splash screen - Screen 0"""
    
    BINDINGS = [
        Binding("q", "quit", "Quitter"),
        Binding("enter", "begin", "Commencer"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static(ASCII_BANNER, id="banner", classes="banner"),
            Static("", classes="spacer"),
            Container(
                Button("⚔️  Entrer dans le Donjon", id="btn-begin", variant="primary", classes="menu-button"),
                Button("📜  Consulter le Grimoire", id="btn-help", variant="default", classes="menu-button"),
                Button("🚪  Fuir vers la Sécurité", id="btn-quit", variant="warning", classes="menu-button"),
                id="menu-buttons",
                classes="menu-container",
            ),
            Static("", classes="spacer"),
            Static(
                "🛡️ [italic]Le Sage conseille : Accomplis ces rituels HORS LIGNE, loin des regards indiscrets...[/italic]",
                id="security-notice",
                classes="notice",
            ),
            id="title-container",
            classes="screen-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-begin":
            self.app.push_screen(ModeSelectScreen())
        elif event.button.id == "btn-help":
            self.app.push_screen(HelpScreen())
        elif event.button.id == "btn-quit":
            self.app.exit()
    
    def action_begin(self) -> None:
        self.app.push_screen(ModeSelectScreen())
    
    def action_quit(self) -> None:
        self.app.exit()


# ============================================================================
# HELP SCREEN
# ============================================================================

class HelpScreen(Screen):
    """Help and information screen"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
        Binding("q", "back", "Retour"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("📜 L'ANCIEN GRIMOIRE DE SAGESSE", classes="screen-title"),
            ScrollableContainer(
                Static(Panel(
                    """[bold italic]"Bienvenue, chercheur de savoir cryptographique..."[/bold italic]

Tu as pénétré dans [bold]DONJON & WALLETS[/bold] — une forge sacrée
où sont forgés les Mots de Pouvoir, mots qui garderont
ton trésor numérique pour l'éternité.

[bold yellow]📖 CHAPITRE I : Les Mots de Pouvoir[/bold yellow]
La phrase de récupération (mnémonique) est une séquence de 12-24 mots sacrés
contenant toute la magie nécessaire pour invoquer ton portefeuille crypto.
Ces incantations suivent l'ancien standard BIP39, reconnu par :
  • Le Royaume Bitcoin (BTC)
  • Les Royaumes Ethereum (ETH)  
  • Tous les coffres majeurs (Ledger, Trezor, MetaMask...)

[bold yellow]📖 CHAPITRE II : Les Trois Rituels Sacrés[/bold yellow]

🎲 [bold]Le Rituel des Dés[/bold] [dim](Voie du Puriste)[/dim]
   Lance tes os sacrés sur la table !
   Les Dieux des Dés calculent : N = (D20-1)×100 + d100
   Jets bénis si N < 1792. Collecte 16 jets bénis.
   [italic]"Le vrai chaos ne s'incline devant aucune machine."[/italic]
   
✨ [bold]Le Rituel Aléatoire[/bold] [dim](Voie de la Commodité)[/dim]
   Invoque les esprits cryptographiques de ta machine.
   Rapide et sûr pour la plupart des aventuriers.
   [italic]"Fais confiance à la machine, si elle est digne."[/italic]
   
🧪 [bold]Le Rituel Hexadécimal[/bold] [dim](Voie de l'Archimage)[/dim]
   Inscris tes propres 32 runes hex d'entropie.
   Pour les maîtres avec sources de chaos externes.
   [italic]"Apporte ta propre magie à la table."[/italic]

[bold red]⚔️ LES COMMANDEMENTS SACRÉS ⚔️[/bold red]
  • Accomplis les rituels HORS LIGNE, hors de portée des ombres
  • Inscris tes mots sur parchemin UNIQUEMENT
  • JAMAIS sur pierre numérique
  • JAMAIS à aucun être, mortel ou numérique
  • Garde dans des coffres fortifiés à travers le royaume
  
[dim italic]Appuie sur ÉCHAP ou Q pour retourner à ta quête...[/dim italic]
""",
                    title="🧙 Savoir Arcanique des Anciens Cryptographes",
                    border_style="blue",
                )),
                id="help-scroll",
            ),
            Button("🔙 Retourner à la Quête", id="btn-back", variant="default"),
            id="help-container",
            classes="screen-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# MODE SELECT SCREEN
# ============================================================================

class ModeSelectScreen(Screen):
    """Choose ritual mode - Screen 1"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
        Binding("1", "select_dice", "Dés"),
        Binding("2", "select_random", "Aléatoire"),
        Binding("3", "select_hex", "Hex"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("⚔️ CHOISIS TA VOIE, AVENTURIER", classes="screen-title"),
            Container(
                Button(
                    "🎲  Le Rituel des Dés  [VOIE DU PURISTE]\n    Lance les os sacrés D20 + d100",
                    id="btn-dice",
                    variant="primary",
                    classes="ritual-button",
                ),
                Button(
                    "✨  Le Rituel Aléatoire  [VOIE RAPIDE]\n    Invoque les esprits cryptographiques",
                    id="btn-random",
                    variant="default",
                    classes="ritual-button",
                ),
                Button(
                    "🧪  Le Rituel Hex  [VOIE DE L'ARCHIMAGE]\n    Inscris 32 runes hexadécimales",
                    id="btn-hex",
                    variant="default",
                    classes="ritual-button",
                ),
                id="ritual-buttons",
                classes="ritual-container",
            ),
            Static(Panel(
                WHY_DICE_TEXT,
                title="🎯 Paroles du Maître du Donjon",
                border_style="yellow",
            ), id="why-dice"),
            Button("🔙 Retourner à l'Entrée", id="btn-back", variant="warning"),
            id="mode-container",
            classes="screen-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-dice":
            self.app.push_screen(DiceRitualScreen())
        elif event.button.id == "btn-random":
            self.app.push_screen(RandomRitualScreen())
        elif event.button.id == "btn-hex":
            self.app.push_screen(HexRitualScreen())
        elif event.button.id == "btn-back":
            self.app.pop_screen()
    
    def action_back(self) -> None:
        self.app.pop_screen()
    
    def action_select_dice(self) -> None:
        self.app.push_screen(DiceRitualScreen())
    
    def action_select_random(self) -> None:
        self.app.push_screen(RandomRitualScreen())
    
    def action_select_hex(self) -> None:
        self.app.push_screen(HexRitualScreen())


# ============================================================================
# DICE RITUAL SCREEN
# ============================================================================

class DiceRitualScreen(Screen):
    """Dice roll entropy collection - Screen 2A"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
    ]
    
    def __init__(self):
        super().__init__()
        self.collector = DiceEntropyCollector(bytes_needed=16)
        self.wordlist = None
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("🎲 LA CHAMBRE DES OS SACRÉS", classes="screen-title"),
            Static(DICE_INSTRUCTIONS, id="dice-instructions", classes="compact-instructions"),
            Horizontal(
                Vertical(
                    Label("Jet D20 (1-20) :"),
                    Input(placeholder="Lance le D20...", id="input-d20"),
                    classes="dice-input-group",
                ),
                Vertical(
                    Label("Jet d100 (0-99) :"),
                    Input(placeholder="Lance le d100...", id="input-d100"),
                    classes="dice-input-group",
                ),
                Button("🎲 Offrir le Jet !", id="btn-roll", variant="primary"),
                id="dice-inputs",
            ),
            Horizontal(
                Static("", id="roll-status", classes="status-text"),
                Static("Bénis : 0/16 | Maudits : 0 | Lancés : 0", id="roll-stats"),
                ProgressBar(total=16, show_eta=False, id="progress"),
                id="stats-section",
            ),
            RichLog(id="roll-log", max_lines=50, highlight=True, markup=True, auto_scroll=True),
            Horizontal(
                Button("🔙 Abandonner le Rituel", id="btn-back", variant="warning"),
                Button("📥 Import Ancien", id="btn-bulk", variant="default"),
                id="bottom-buttons",
            ),
            id="dice-container",
            classes="screen-container",
        )
    
    def on_mount(self) -> None:
        """Load wordlist on mount"""
        try:
            self.wordlist = load_wordlist(WORDLIST_PATH)
        except Exception as e:
            self.notify(f"Erreur de chargement : {e}", severity="error")
        
        # Focus on first input
        self.query_one("#input-d20", Input).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-roll":
            self._process_roll()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-bulk":
            self.app.push_screen(BulkImportScreen(self.collector, self.wordlist))
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in inputs"""
        if event.input.id == "input-d20":
            self.query_one("#input-d100", Input).focus()
        elif event.input.id == "input-d100":
            self._process_roll()
    
    def _process_roll(self) -> None:
        """Process a dice roll"""
        if self.collector.is_complete:
            return
        
        d20_input = self.query_one("#input-d20", Input)
        d100_input = self.query_one("#input-d100", Input)
        roll_log = self.query_one("#roll-log", RichLog)
        
        # Check for empty inputs
        d20_val = d20_input.value.strip()
        d100_val = d100_input.value.strip()
        
        if not d20_val:
            self.notify("⚠️ Le D20 attend ton jet ! (1-20)", severity="warning")
            d20_input.focus()
            return
        if not d100_val:
            self.notify("⚠️ Lance aussi le d100 ! (0-99)", severity="warning")
            d100_input.focus()
            return
        
        try:
            d20 = int(d20_val)
            d100 = int(d100_val)
            
            if not (1 <= d20 <= 20):
                self.notify("Le D20 ne parle que de 1 à 20 !", severity="warning")
                return
            if not (0 <= d100 <= 99):
                self.notify("Le d100 ne parle que de 0 à 99 !", severity="warning")
                return
            
            result = self.collector.add_roll(d20, d100)
            stats = self.collector.stats
            
            # Update log
            n_value = result.roll_value
            if result.accepted:
                roll_log.write(f"[green]✅ Jet #{stats.total_rolls}: D20={d20}, d100={d100} → N={n_value} [LES DIEUX ACCEPTENT !][/green]")
                status_text = f"[green]✅ Béni ! N={n_value} < 1792[/green]"
            else:
                roll_log.write(f"[red]❌ Jet #{stats.total_rolls}: D20={d20}, d100={d100} → N={n_value} [MAUDIT ! Relance !][/red]")
                status_text = f"[red]❌ Maudit ! N={n_value} ≥ 1792, les Dieux en demandent un autre ![/red]"
            
            # Update status
            self.query_one("#roll-status", Static).update(status_text)
            self.query_one("#roll-stats", Static).update(
                f"Bénis : {stats.accepted_rolls}/16  |  "
                f"Maudits : {stats.rejected_rolls}  |  "
                f"Lancés : {stats.total_rolls}"
            )
            
            # Update progress
            self.query_one("#progress", ProgressBar).update(progress=stats.accepted_rolls)
            
            # Clear inputs and refocus
            d20_input.value = ""
            d100_input.value = ""
            d20_input.focus()
            
            # Check if complete
            if self.collector.is_complete:
                self._complete_ritual()
                
        except ValueError as e:
            self.notify(f"Entrée invalide : {e}", severity="error")
    
    def _complete_ritual(self) -> None:
        """Complete the ritual and show reveal screen"""
        try:
            entropy = self.collector.get_entropy()
            mnemonic = entropy_to_mnemonic(entropy, self.wordlist)
            stats = self.collector.stats
            
            self.app.push_screen(RevealScreen(
                mnemonic=mnemonic,
                entropy_hex=entropy.hex(),
                method="Rituel des Dés Sacrés",
                stats_info=f"Lancés : {stats.total_rolls} | Bénis : {stats.accepted_rolls} | Maudits : {stats.rejected_rolls}"
            ))
        except Exception as e:
            self.notify(f"Le rituel a échoué : {e}", severity="error")
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# BULK IMPORT SCREEN
# ============================================================================

class BulkImportScreen(Screen):
    """Bulk import N values - Advanced option"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
    ]
    
    def __init__(self, collector: DiceEntropyCollector, wordlist: List[str]):
        super().__init__()
        self.collector = collector
        self.wordlist = wordlist
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("📥 IMPORT DU PARCHEMIN ANCIEN", classes="screen-title"),
            Static(Panel(
                """[italic]"Tu apportes des offrandes pré-calculées aux Dieux..."[/italic]
                
Entre les valeurs N (0-1999) d'un oracle externe, séparées par des virgules.

Exemple d'incantation : 442, 1234, 567, 890, 123, 456, 789...

Les valeurs ≥ 1792 seront maudites et rejetées.
Tu as besoin de 16 offrandes bénies pour compléter le rituel.""",
                title="📋 Le Format des Offrandes",
                border_style="cyan",
            )),
            Input(
                placeholder="Inscris les valeurs N, séparées par des virgules...",
                id="input-bulk",
            ),
            Container(
                Button("✅ Offrir aux Dieux", id="btn-import", variant="primary"),
                Button("🔙 Retour", id="btn-back", variant="warning"),
                classes="button-row",
            ),
            Static("", id="import-result"),
            id="bulk-container",
            classes="screen-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-import":
            self._process_import()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
    
    def _process_import(self) -> None:
        """Process bulk import"""
        input_field = self.query_one("#input-bulk", Input)
        result_display = self.query_one("#import-result", Static)
        
        try:
            values_str = input_field.value.replace(" ", "")
            values = [int(v.strip()) for v in values_str.split(",") if v.strip()]
            
            accepted = 0
            rejected = 0
            
            for n in values:
                if self.collector.is_complete:
                    break
                try:
                    result = self.collector.add_n_value(n)
                    if result.accepted:
                        accepted += 1
                    else:
                        rejected += 1
                except ValueError:
                    rejected += 1
            
            stats = self.collector.stats
            result_display.update(
                f"[green]Offrandes reçues : {accepted} bénies, {rejected} maudites. "
                f"Entropie collectée : {stats.bytes_collected}/16 octets[/green]"
            )
            
            if self.collector.is_complete:
                self._complete_ritual()
                
        except Exception as e:
            result_display.update(f"[red]Les Dieux rejettent ces offrandes : {e}[/red]")
    
    def _complete_ritual(self) -> None:
        """Complete the ritual"""
        try:
            entropy = self.collector.get_entropy()
            mnemonic = entropy_to_mnemonic(entropy, self.wordlist)
            stats = self.collector.stats
            
            # Pop bulk screen first
            self.app.pop_screen()
            # Then push reveal screen
            self.app.push_screen(RevealScreen(
                mnemonic=mnemonic,
                entropy_hex=entropy.hex(),
                method="Import Parchemin Ancien",
                stats_info=f"Offrandes : {stats.total_rolls} | Bénies : {stats.accepted_rolls}"
            ))
        except Exception as e:
            self.notify(f"Le rituel a échoué : {e}", severity="error")
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# RANDOM RITUAL SCREEN
# ============================================================================

class RandomRitualScreen(Screen):
    """Random entropy generation - Screen 2B"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
    ]
    
    def __init__(self):
        super().__init__()
        self.wordlist = None
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("✨ LA CHAMBRE DES ESPRITS NUMÉRIQUES", classes="screen-title"),
            Static(Panel(
                """[italic]"Tu as choisi la voie rapide, aventurier..."[/italic]

Ce rituel invoque les esprits cryptographiques qui résident
dans ta machine pour conjurer l'entropie de l'éther numérique.

Retiens ces avertissements :
• Les esprits de ta machine doivent être loyaux
• Le silicium doit être exempt de sombres enchantements
• Lance ce sort hors ligne pour une protection maximale

Quand ton courage est prêt, invoque les esprits
pour révéler tes 12 Mots de Pouvoir.""",
                title="🌟 L'Invocation des Esprits Cryptographiques",
                border_style="magenta",
            ), id="random-info"),
            Container(
                Button(
                    "⚡ Invoquer les Esprits !",
                    id="btn-generate",
                    variant="primary",
                    classes="big-button",
                ),
                classes="center-container",
            ),
            Button("🔙 Retraite", id="btn-back", variant="warning"),
            id="random-container",
            classes="screen-container",
        )
    
    def on_mount(self) -> None:
        try:
            self.wordlist = load_wordlist(WORDLIST_PATH)
        except Exception as e:
            self.notify(f"Erreur de chargement : {e}", severity="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate":
            self._generate()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
    
    def _generate(self) -> None:
        """Generate random mnemonic"""
        try:
            entropy = random_entropy(16)
            mnemonic = entropy_to_mnemonic(entropy, self.wordlist)
            
            self.app.push_screen(RevealScreen(
                mnemonic=mnemonic,
                entropy_hex=entropy.hex(),
                method="Invocation des Esprits",
                stats_info="Esprits cryptographiques 128 bits"
            ))
        except Exception as e:
            self.notify(f"Les esprits ont échoué : {e}", severity="error")
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# HEX RITUAL SCREEN
# ============================================================================

class HexRitualScreen(Screen):
    """Hex entropy input - Screen 2C"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
    ]
    
    def __init__(self):
        super().__init__()
        self.wordlist = None
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("🧪 LE SANCTUAIRE DE L'ARCHIMAGE", classes="screen-title"),
            Static(Panel(
                """[italic]"Ah, tu apportes ta propre magie à la table..."[/italic]

Inscris ton entropie sous forme de 32 runes hexadécimales.
(16 octets = 128 bits = 12 Mots de Pouvoir)

Exemples anciens :
• a1b2c3d4e5f6789012345678abcdef00
• 0xa1b2c3d4e5f6789012345678abcdef00

Seuls les glyphes sacrés 0-9 et a-f sont permis.
Le préfixe "0x" est optionnel.""",
                title="🧙 Le Grimoire des Inscriptions Hex",
                border_style="green",
            ), id="hex-info"),
            Container(
                Label("Inscris 32 runes hex :"),
                Input(
                    placeholder="Inscris ton entropie ici...",
                    id="input-hex",
                    validators=[HexValidator()],
                    max_length=66,  # Allow for 0x prefix
                ),
                Static("", id="hex-validation"),
                classes="input-group",
            ),
            Container(
                Button("🔮 Lancer le Sort Hex !", id="btn-generate", variant="primary"),
                Button("🔙 Retraite", id="btn-back", variant="warning"),
                classes="button-row",
            ),
            id="hex-container",
            classes="screen-container",
        )
    
    def on_mount(self) -> None:
        try:
            self.wordlist = load_wordlist(WORDLIST_PATH)
        except Exception as e:
            self.notify(f"Erreur de chargement : {e}", severity="error")
        
        self.query_one("#input-hex", Input).focus()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate hex input as user types"""
        if event.input.id == "input-hex":
            value = event.value
            validation_display = self.query_one("#hex-validation", Static)
            
            if not value:
                validation_display.update("")
                return
            
            is_valid, error = validate_hex_input(value, 16)
            if is_valid:
                validation_display.update("[green]✅ Les runes sont valides ![/green]")
            else:
                validation_display.update(f"[yellow]⚠️ {error}[/yellow]")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate":
            self._generate()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-hex":
            self._generate()
    
    def _generate(self) -> None:
        """Generate mnemonic from hex"""
        hex_input = self.query_one("#input-hex", Input)
        
        is_valid, error = validate_hex_input(hex_input.value, 16)
        if not is_valid:
            self.notify(error, severity="error")
            return
        
        try:
            entropy = hex_to_entropy(hex_input.value)
            mnemonic = entropy_to_mnemonic(entropy, self.wordlist)
            
            self.app.push_screen(RevealScreen(
                mnemonic=mnemonic,
                entropy_hex=entropy.hex(),
                method="Rituel Hex",
                stats_info="Entropie fournie par l'Archimage"
            ))
        except Exception as e:
            self.notify(f"Le sort a échoué : {e}", severity="error")
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# REVEAL SCREEN
# ============================================================================

class RevealScreen(Screen):
    """Reveal mnemonic with safety warnings - Screen 3"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
    ]
    
    revealed = reactive(False)
    
    def __init__(
        self,
        mnemonic: str,
        entropy_hex: str,
        method: str,
        stats_info: str,
    ):
        super().__init__()
        self.mnemonic = mnemonic
        self.entropy_hex = entropy_hex
        self.method = method
        self.stats_info = stats_info
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("📜 LE PARCHEMIN SACRÉ ATTEND", classes="screen-title"),
            Static(Panel(
                SECURITY_WARNING,
                title="⚔️ L'AVERTISSEMENT DU GARDIEN",
                border_style="red",
            ), id="warning-panel"),
            Container(
                Static("[italic]Les Mots de Pouvoir sont cachés. Prononce 'REVELER' pour briser le sceau.[/italic]", id="reveal-prompt"),
                Input(
                    placeholder="Murmure REVELER pour dévoiler les mots sacrés...",
                    id="input-reveal",
                    password=True,
                ),
                id="reveal-input-section",
            ),
            Container(
                Static(self._get_masked_panel(), id="mnemonic-display"),
                id="mnemonic-section",
            ),
            Static(f"Rituel: {self.method} | {self.stats_info}", id="method-info", classes="dim-text"),
            Container(
                Button("✅ Quête Accomplie", id="btn-done", variant="primary"),
                Button("💼 Voir Tes Coffres", id="btn-export", variant="success"),
                Button("⚠️ Exporter sur Parchemin", id="btn-export-mnemonic", variant="warning", disabled=True),
                id="action-buttons",
                classes="button-row",
            ),
            id="reveal-container",
            classes="screen-container",
        )
    
    def _get_masked_panel(self) -> Panel:
        """Get masked mnemonic panel"""
        masked = mask_mnemonic(self.mnemonic)
        return Panel(
            masked,
            title="🔒 Les Mots de Pouvoir (Scellés)",
            border_style="dim",
        )
    
    def _get_revealed_panel(self) -> Panel:
        """Get revealed mnemonic panel"""
        words = self.mnemonic.split()
        
        # Format words in numbered grid
        lines = []
        for i in range(0, len(words), 4):
            row = []
            for j, word in enumerate(words[i:i+4]):
                num = i + j + 1
                row.append(f"{num:2d}. {word:<12}")
            lines.append("  ".join(row))
        
        formatted = "\n".join(lines)
        
        return Panel(
            formatted,
            title="🔓 LES MOTS DE POUVOIR - INSCRIS SUR PARCHEMIN, PUIS DÉTRUIS CE ROULEAU",
            border_style="green",
        )
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Check for REVELER input"""
        if event.input.id == "input-reveal":
            if event.value.upper() == "REVELER":
                self._reveal_mnemonic()
    
    def _reveal_mnemonic(self) -> None:
        """Reveal the mnemonic"""
        self.revealed = True
        
        # Update display
        mnemonic_display = self.query_one("#mnemonic-display", Static)
        mnemonic_display.update(self._get_revealed_panel())
        
        # Hide reveal input section
        reveal_section = self.query_one("#reveal-input-section", Container)
        reveal_section.display = False
        
        # Enable export mnemonic button
        export_btn = self.query_one("#btn-export-mnemonic", Button)
        export_btn.disabled = False
        
        self.notify("⚔️ Le sceau est brisé ! Inscris ces mots et garde-les précieusement !", severity="warning")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-done":
            self._return_to_title()
        elif event.button.id == "btn-export":
            self.app.push_screen(ExportPublicScreen(self.mnemonic))
        elif event.button.id == "btn-export-mnemonic":
            self.app.push_screen(ExportMnemonicScreen(self.mnemonic, self.entropy_hex))
    
    def _return_to_title(self) -> None:
        """Return to title screen, clearing history"""
        # Switch to a fresh TitleScreen (replaces entire screen stack)
        self.app.switch_screen(TitleScreen())
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# EXPORT PUBLIC INFO SCREEN
# ============================================================================

class ExportPublicScreen(Screen):
    """Export public wallet information - Screen 4"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
    ]
    
    def __init__(self, mnemonic: str):
        super().__init__()
        self.mnemonic = mnemonic
        self.wallets: List[WalletInfo] = []
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("� YOUR TREASURE VAULTS", classes="screen-title"),
            Static(Panel(
                "[italic]\"The spirits reveal your vault addresses...\"[/italic]\n\n"
                "These sigils are SAFE to share — they allow others\n"
                "to deposit tribute into your vaults.",
                title="🔓 Public Runes (Safe to Share)",
                border_style="blue",
            ), id="export-info"),
            ScrollableContainer(
                Static("", id="wallet-display"),
                id="wallet-scroll",
            ),
            Container(
                Button("💾 Inscribe to Scroll", id="btn-save", variant="primary"),
                Button("🔙 Return", id="btn-back", variant="warning"),
                classes="button-row",
            ),
            Static("", id="save-status"),
            id="export-container",
            classes="screen-container",
        )
    
    def on_mount(self) -> None:
        """Derive wallet addresses"""
        try:
            self.wallets = derive_wallet_info(self.mnemonic)
            self._display_wallets()
        except Exception as e:
            self.notify(f"Les esprits ont échoué à révéler : {e}", severity="error")
    
    def _display_wallets(self) -> None:
        """Display wallet information with QR codes"""
        display = self.query_one("#wallet-display", Static)
        
        panels = []
        for wallet in self.wallets:
            icon = "🔷" if wallet.chain == "Ethereum" else "🟠"
            realm = "Royaume Ethereum" if wallet.chain == "Ethereum" else "Royaume Bitcoin"
            
            # Generate QR code if available
            qr_text = ""
            if HAS_QRCODE:
                qr_text = self._generate_ascii_qr(wallet.address)
            else:
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={wallet.address}"
                qr_text = f"\n📱 Rune d'Invocation : {qr_url}"
            
            panel_content = f"""{icon} {realm.upper()}

Sceau du Coffre : {wallet.address}
Chemin Ancestral : {wallet.path}

Portail de Divination : {wallet.explorer_url}
{qr_text}
"""
            panels.append(Panel(panel_content, title=f"💼 Coffre {realm}", border_style="cyan"))
        
        display.update(Group(*panels))
    
    def _generate_ascii_qr(self, data: str) -> str:
        """Generate ASCII QR code"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Generate ASCII art
            lines = []
            lines.append("\n📱 Rune d'Invocation (scanne pour recevoir des tributs) :")
            matrix = qr.get_matrix()
            for row in matrix:
                line = ""
                for cell in row:
                    line += "██" if cell else "  "
                lines.append(line)
            return "\n".join(lines)
        except Exception:
            return "\n📱 Échec de la génération de la rune"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save_to_file()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
    
    def _save_to_file(self) -> None:
        """Save public info to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sceaux_coffres_{timestamp}.txt"
        
        try:
            content = [
                "=" * 60,
                "⚔️ DONJON & WALLETS - Tes Sceaux de Coffres au Trésor ⚔️",
                f"Inscrit le : {datetime.now().isoformat()}",
                "=" * 60,
                "",
                "✅ Ces sceaux sont SÛRS à partager pour recevoir des tributs.",
                "🚫 Ne JAMAIS partager tes Mots de Pouvoir (phrase secrète) !",
                "",
            ]
            
            for wallet in self.wallets:
                realm = "Royaume Ethereum" if wallet.chain == "Ethereum" else "Royaume Bitcoin"
                content.extend([
                    "-" * 40,
                    f"COFFRE {realm.upper()}",
                    "-" * 40,
                    f"Sceau du Coffre : {wallet.address}",
                    f"Chemin Ancestral : {wallet.path}",
                    f"Portail de Divination : {wallet.explorer_url}",
                    "",
                ])
            
            filepath = Path.cwd() / filename
            with open(filepath, "w") as f:
                f.write("\n".join(content))
            
            status = self.query_one("#save-status", Static)
            status.update(f"[green]✅ Inscrit dans {filename}[/green]")
            self.notify(f"Parchemin inscrit : {filename}", severity="information")
            
        except Exception as e:
            self.notify(f"L'inscription a échoué : {e}", severity="error")
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# EXPORT MNEMONIC SCREEN
# ============================================================================

class ExportMnemonicScreen(Screen):
    """Export mnemonic with extra confirmation - DANGEROUS"""
    
    BINDINGS = [
        Binding("escape", "back", "Retour"),
    ]
    
    def __init__(self, mnemonic: str, entropy_hex: str):
        super().__init__()
        self.mnemonic = mnemonic
        self.entropy_hex = entropy_hex
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("☠️ LE RITUEL INTERDIT", classes="screen-title danger"),
            Static(Panel(
                """[bold red]🚨 GRAVE DANGER DEVANT TOI 🚨[/bold red]

[italic]"Aventurier, tu foules un sol maudit..."[/italic]

Tu cherches à inscrire les Mots de Pouvoir sur un parchemin numérique.
Cet acte entraîne de TERRIBLES CONSÉQUENCES :

• Les démons de l'ombre (malwares) peuvent voler le parchemin
• Les esprits du nuage peuvent le copier à ton insu
• Même les parchemins détruits laissent des traces spectrales
• Toute créature possédant ce parchemin POSSÈDE ton trésor entier

Procède UNIQUEMENT si tu acceptes ces périls et que tu as
un but sacré (comme créer une copie sur papier).

Prononce les mots [bold]"JE COMPRENDS LE DANGER"[/bold] pour continuer...""",
                title="☠️ LA MALÉDICTION DE L'INSCRIPTION NUMÉRIQUE",
                border_style="red",
            ), id="danger-warning"),
            Input(
                placeholder='Prononce : "JE COMPRENDS LE DANGER"',
                id="input-confirm",
            ),
            Container(
                Button("☠️ Accepter la Malédiction", id="btn-export", variant="error", disabled=True),
                Button("🔙 Fuir vers la Sécurité", id="btn-back", variant="primary"),
                classes="button-row",
            ),
            Static("", id="export-status"),
            id="export-mnemonic-container",
            classes="screen-container",
        )
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Check for confirmation phrase"""
        if event.input.id == "input-confirm":
            export_btn = self.query_one("#btn-export", Button)
            if event.value.upper() == "JE COMPRENDS LE DANGER":
                export_btn.disabled = False
            else:
                export_btn.disabled = True
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-export":
            self._export_mnemonic()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
    
    def _export_mnemonic(self) -> None:
        """Export mnemonic to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"PARCHEMIN_MAUDIT_{timestamp}.txt"
        
        try:
            content = [
                "=" * 60,
                "☠️☠️☠️ PARCHEMIN MAUDIT - MOTS DE POUVOIR - MAUDIT ☠️☠️☠️",
                "=" * 60,
                "",
                "Ce parchemin contient ta CLÉ MAÎTRESSE vers tout ton trésor.",
                "Toute créature le possédant peut réclamer ton butin entier.",
                "",
                "⚔️ DÉTRUIS CE PARCHEMIN IMMÉDIATEMENT APRÈS L'AVOIR ⚔️",
                "⚔️ INSCRIT SUR UN SUPPORT PERMANENT ! ⚔️",
                "",
                "=" * 60,
                "LES DOUZE MOTS DE POUVOIR (Mnémonique BIP39)",
                "=" * 60,
                "",
                self.mnemonic,
                "",
                "=" * 60,
                "L'ENTROPIE BRUTE (Runes Hex)",
                "=" * 60,
                "",
                self.entropy_hex,
                "",
                f"Conjuré le : {datetime.now().isoformat()}",
                "Conjuré par : Donjon & Wallets",
                "",
                "☠️ BRÛLE CE PARCHEMIN APRÈS LECTURE ! ☠️",
            ]
            
            filepath = Path.cwd() / filename
            with open(filepath, "w") as f:
                f.write("\n".join(content))
            
            status = self.query_one("#export-status", Static)
            status.update(f"[red]☠️ Parchemin maudit créé : {filename} - DÉTRUIS APRÈS USAGE ![/red]")
            self.notify(f"☠️ Parchemin maudit inscrit : {filename}", severity="warning")
            
        except Exception as e:
            self.notify(f"Le rituel a échoué : {e}", severity="error")
    
    def action_back(self) -> None:
        self.app.pop_screen()


# ============================================================================
# MAIN APP
# ============================================================================

class DungeonWalletsApp(App):
    """Dungeon & Wallets - BIP39 Mnemonic Generator"""
    
    CSS = """
    /* Base screen styling */
    Screen {
        background: $surface;
    }
    
    /* Fix button text highlighting */
    Button {
        text-style: bold;
    }
    
    Button:focus {
        text-style: bold;
    }
    
    Button > .button--label {
        text-style: bold;
        background: transparent;
    }
    
    .screen-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    
    .screen-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1;
        margin-bottom: 1;
        border: heavy $primary;
        background: $surface-darken-1;
    }
    
    .screen-title.danger {
        color: $error;
        border: heavy $error;
    }
    
    /* Banner styling */
    .banner {
        text-align: center;
        color: $primary;
        margin: 2 0;
    }
    
    .spacer {
        height: 1;
    }
    
    /* Menu buttons */
    .menu-container {
        align: center middle;
        width: 100%;
        height: auto;
    }
    
    .menu-button {
        width: 40;
        margin: 1;
    }
    
    /* Notice text */
    .notice {
        text-align: center;
        color: $warning;
        margin-top: 2;
    }
    
    /* Ritual buttons */
    .ritual-container {
        width: 100%;
        align: center middle;
    }
    
    .ritual-button {
        width: 50;
        height: 5;
        margin: 1;
    }
    
    /* Input groups */
    .input-group {
        margin: 1 0;
    }
    
    .dice-input-group {
        width: 25;
        height: 5;
        margin: 0 2;
    }
    
    .dice-input-group Input {
        width: 100%;
        height: 3;
        background: $surface;
        color: $text;
    }
    
    Input {
        background: $surface;
        color: $text;
    }
    
    Input:focus {
        border: tall $primary;
    }
    
    .dice-input-group Label {
        height: 1;
    }
    
    .compact-instructions {
        text-align: center;
        color: $text-muted;
        padding: 0 1;
        height: 2;
    }
    
    #dice-inputs {
        height: 5;
        align: center middle;
    }
    
    /* Button rows */
    .button-row {
        height: auto;
        align: center middle;
        margin: 1 0;
    }
    
    .button-row Button {
        margin: 0 1;
    }
    
    /* Center containers */
    .center-container {
        align: center middle;
        height: auto;
    }
    
    .big-button {
        width: 40;
        height: 5;
    }
    
    /* Stats section */
    #stats-section {
        height: 3;
        align: center middle;
        padding: 0 1;
    }
    
    .status-text {
        width: auto;
        margin-right: 2;
    }
    
    #roll-stats {
        width: auto;
        color: $text-muted;
        margin-right: 2;
    }
    
    #progress {
        width: 30;
    }
    
    /* Log section */
    #roll-log {
        height: 1fr;
        margin: 1 0;
        border: solid $secondary;
        background: $surface-darken-2;
        scrollbar-size: 0 0;
    }
    
    #bottom-buttons {
        height: 3;
        align: center middle;
        dock: bottom;
    }
    
    /* Scrollable containers */
    ScrollableContainer {
        height: 1fr;
        margin: 1 0;
    }
    
    #help-scroll {
        height: 1fr;
    }
    
    #wallet-scroll {
        height: 1fr;
        border: solid $primary;
    }
    
    /* Dim text */
    .dim-text {
        color: $text-muted;
        text-align: center;
    }
    
    /* Mnemonic display */
    #mnemonic-section {
        margin: 2 0;
        padding: 1;
    }
    
    /* Bottom buttons */
    #bottom-buttons {
        dock: bottom;
        height: auto;
        padding: 1;
    }
    
    #action-buttons {
        height: auto;
        align: center middle;
        margin: 1 0;
    }
    
    #action-buttons Button {
        margin: 0 1;
    }
    
    /* Reveal section */
    #reveal-input-section {
        align: center middle;
        height: 5;
        margin: 1 0;
    }
    
    #reveal-prompt {
        text-align: center;
        height: 1;
    }
    
    #input-reveal {
        width: 50;
        height: 3;
    }
    
    /* Warning panel */
    #warning-panel {
        margin: 1 0;
    }
    
    /* Why dice panel */
    #why-dice {
        margin: 1 0;
    }
    
    /* Validation display */
    #hex-validation {
        text-align: center;
        margin: 1;
    }
    
    /* Progress bar */
    ProgressBar {
        width: 50%;
        margin: 1 2;
    }
    """
    
    TITLE = "⚔️ Donjon & Wallets ⚔️"
    SUB_TITLE = "Lance les Dés. Scelle ton Destin."
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quitter", priority=True),
        Binding("ctrl+c", "quit", "Quitter", priority=True, show=False),
    ]
    
    def on_mount(self) -> None:
        """Start with title screen"""
        self.push_screen(TitleScreen())
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    # Check for required files
    if not WORDLIST_PATH.exists():
        print(f"❌ Error: Wordlist file not found at {WORDLIST_PATH}")
        print("   Please ensure 'english.txt' is in the same directory.")
        sys.exit(1)
    
    app = DungeonWalletsApp()
    app.run()


if __name__ == "__main__":
    main()

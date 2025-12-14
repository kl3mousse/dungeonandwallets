# Donjon & Wallet (D&W)

> 🎲 Lance les dés. Scelle ton destin. ⚔️

Application terminal thématique D&D pour générer des phrases mnémoniques BIP39 en toute sécurité.

![Terminal UI](https://img.shields.io/badge/UI-Textual%20TUI-blue)
![BIP39](https://img.shields.io/badge/Standard-BIP39-green)
![Offline](https://img.shields.io/badge/Mode-Offline-yellow)

## Résumé

![Accueil](./screenshots/screenshot1.png)

![Choix](./screenshots/screenshot2.png)

![Dés](./screenshots/screenshot3.png)

### génération de seed avec 1 D20 et 1 D100
![Révélation](./screenshots/screenshot4.png)

![Coffres](./screenshots/screenshot5.png)

### Affichage des clefs publiques BTC ETH
![Export](./screenshots/screenshot6.png)

## Installation

```bash
pip install textual rich
python dw_app.py
```

## Trois Rituels

| Rituel | Description |
|--------|-------------|
| 🎲 **Rituel des Dés** | Entropie via D20 + d100 physiques (recommandé) |
| ✨ **Rituel Aléatoire** | Générateur cryptographique du système |
| 🧪 **Rituel Hex** | Ta propre entropie (32 caractères hex) |

## Pourquoi les Dés Physiques ?

- ✦ Aucune vulnérabilité logicielle
- ✦ Aucune porte dérobée matérielle
- ✦ Entropie vérifiable
- ✦ Confiance maximale

## Sécurité

⚠️ **Pratiques essentielles :**

- Exécute **HORS LIGNE**
- Inscris sur **PAPIER uniquement**
- **Ne partage JAMAIS** ta phrase secrète
- **Jamais de capture d'écran**

## Structure

```
├── dw_app.py      # Application TUI Textual
├── core.py        # Fonctions entropie/mnémonique
├── english.txt    # Liste BIP39 (2048 mots)
└── screenshots/   # Captures d'écran
```

## Raccourcis

| Touche | Action |
|--------|--------|
| `Entrée` | Confirmer |
| `Échap` | Retour |
| `Tab` | Champ suivant |
| `Ctrl+Q` | Quitter |

## Licence

MIT.

---

# 🎲🎲🎲

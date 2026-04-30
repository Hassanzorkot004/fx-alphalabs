# FX AlphaLab v2 — Project Overview

## 1. Objectif du projet

FX AlphaLab v2 est un système de génération de signaux FX basé sur trois agents spécialisés :
- un agent macro-économique,
- un agent technique,
- un agent de sentiment.

Le système combine ces agents avec un orchestrateur LLM qui produit une direction finale (`BUY`, `SELL`, `HOLD`) accompagnée d’une explication. Les modèles sont entraînés avec `train_agents.py` et utilisés en production avec `run_agent.py`.

## 2. Structure principale

### 2.1 `train_agents.py`

C’est le script principal de training. Il réalise :
- téléchargement de données OHLCV sur ~4 ans via `yfinance`,
- construction de features techniques, macro et sentiment,
- calcul des targets (SELL/HOLD/BUY),
- entraînement de trois agents,
- sauvegarde des modèles dans `outputs/models/`.

### 2.2 `run_agent.py`

C’est le script de production / live agent. Il réalise :
- chargement des modèles entraînés,
- collecte des données live : prix, macro et news,
- exécution des trois agents en mode prédiction,
- passage des résultats à l’orchestrateur LLM,
- sauvegarde du signal dans `outputs/signals.csv`.

### 2.3 `configs/agent_config.yaml`

Ce fichier de configuration contient :
- les paires FX surveillées (`EURUSD=X`, `GBPUSD=X`, `USDJPY=X`),
- la fréquence du cycle (`1h`, toutes les 60 minutes),
- les chemins des données et modèles,
- les paramètres FRED, RSS et LLM,
- les hyperparamètres des agents macro/technique/sentiment.

## 3. Agents

### 3.1 `MacroAgent` (`agents/macro_agent.py`)

- Entraînement : `MacroAgent.fit()`
- Sauvegarde : `MacroAgent.save()`
- Chargement : `MacroAgent.load()`
- Prédiction live : `MacroAgent.predict_live()`

Fonctionnement :
- utilise des features macro FRED (`yield_10y`, `yield_2y`, `vix`),
- calcule `mac_yield_z`, `mac_macro_strength`, `mac_vix_z`, etc.,
- effectue un clustering KMeans en `n_states = 3`,
- classe les clusters en `bullish`, `neutral`, `bearish` via des règles absolues.

Fichier de modèle enregistré :
- `outputs/models/macro/ssl_hmm.pkl`

### 3.2 `TechnicalAgent` (`agents/technical_agent.py`)

- Entraînement : `TechnicalAgent.fit()`
- Sauvegarde : `TechnicalAgent.save()`
- Chargement : `TechnicalAgent.load()`
- Prédiction live : `TechnicalAgent.predict_live()`

Fonctionnement :
- entraîne un réseau TCN/LSTM par paire FX,
- utilise des features techniques comme RSI, MACD, ATR, Bollinger, chandeliers, sessions horaires,
- normalise les entrées avec un `RobustScaler`,
- fait un early-stopping basé sur F1 score de validation,
- sauvegarde un modèle par paire : `tech_model_{pair}.pt` et un scaler `tech_scaler.pkl`.

Fichiers de modèle enregistrés :
- `outputs/models/technical/tech_scaler.pkl`
- `outputs/models/technical/tech_model_{pair}.pt`

### 3.3 `SentimentAgent` (`agents/sentiment_agent.py`)

- Entraînement : `SentimentAgent.fit()`
- Sauvegarde : `SentimentAgent.save()`
- Chargement : `SentimentAgent.load()`
- Prédiction live : `SentimentAgent.predict_live()`

Fonctionnement :
- utilise un `LogisticRegression` sur des features de sentiment calculées à partir de titres RSS,
- features stables entre training et live : `nws_sent_signal`, `nws_sent_fast`, `nws_sent_slow`, etc.,
- en live, si le score lexical est clair, le signal direct est utilisé plutôt que le modèle.

Fichier de modèle enregistré :
- `outputs/models/sentiment/sent_model.pkl`

## 4. Sources de données

### 4.1 `PriceFeed` (`data_feed/price_feed.py`)

- télécharge les données horaires via `yfinance`,
- normalise les colonnes OHLCV,
- calcule toutes les features techniques nécessaires pour `TechnicalAgent`.

### 4.2 `MacroFeed` (`data_feed/macro_feed.py`)

- récupère les séries FRED : `DGS10`, `DGS2`, `VIXCLS`,
- construit les features macro `mac_*`,
- ajoute les features de carry par paire (`pair_carry_signal`) à partir des rendements étrangers de 10 ans.

### 4.3 `NewsFeed` (`data_feed/news_feed.py`)

- collecte des articles via RSS,
- filtre et classe la pertinence par paire FX,
- calcule un score de sentiment basé sur des mots bullish / bearish,
- produit des features de news utilisables par `SentimentAgent`.

## 5. Orchestrateur LLM

### `orchestrator/orchestrator.py`

- reçoit les sorties des trois agents,
- construit un prompt JSON pour le modèle Llama 3.1 8B via Ollama,
- demande au modèle de choisir direction, raisonnement, `key_driver` et `risk_note`.

### Règles additionnelles

- la confiance finale n’est PAS extraite du LLM,
- elle est calculée en Python via `compute_signal_confidence()` en fonction de l’accord entre agents,
- la position size dépend de ce score et du niveau d’accord (`FULL`, `PARTIAL`, `CONFLICT`).

## 6. Exécution

### Entraînement

```bash
python train_agents.py
```

Ce script génère les modèles dans :
- `outputs/models/macro/`
- `outputs/models/technical/`
- `outputs/models/sentiment/`

### Live / test

```bash
python run_agent.py --once
```

ou pour tourner en boucle toutes les 60 minutes :

```bash
python run_agent.py
```

### Configuration

Les paramètres sont centralisés dans `configs/agent_config.yaml`, notamment :
- paires FX,
- intervalle `1h`,
- chemins de sortie,
- sources FRED et RSS,
- hyperparamètres des agents.

## 7. Résultats

### Sorties principales

- `outputs/signals.csv` : historique des signaux générés en live,
- `outputs/models/...` : modèles entraînés utilisés par le live agent,
- `outputs/context.json` : mémoire de signal pour l’orchestrateur.

## 8. Notes importantes

- `run_agent.py` ne fait pas d’entraînement : il charge uniquement les modèles existants.
- Le training est exécuté dans `train_agents.py`.
- Si un modèle manque, `run_agent.py` arrête l’exécution et affiche un message.
- Le LLM est utilisé principalement pour le texte explicatif et la direction, pas pour la confiance finale.

---

Ce document présente l’architecture et le fonctionnement du projet FX AlphaLab v2. Il peut servir de base pour un README plus détaillé ou pour une documentation utilisateur.
# Tabula Silico — lancement de la campagne experimentale
# Usage :  .\lancer.ps1
# ou    :  powershell -ExecutionPolicy Bypass -File .\lancer.ps1

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Verifications prealables — AVANT de lancer 2 heures de calcul
# ---------------------------------------------------------------------------

$python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "ARRET : $python introuvable." -ForegroundColor Red
    Write-Host "  Cree l'environnement :  python -m venv venv"
    exit 1
}

& $python -c "import neat, numpy, pygame" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ARRET : dependances manquantes dans le venv." -ForegroundColor Red
    Write-Host "  Installe-les :  .\venv\Scripts\pip.exe install -r requirements.txt"
    exit 1
}

if (-not (Test-Path "runs")) { New-Item -ItemType Directory -Path "runs" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

# ---------------------------------------------------------------------------
# Les runs
# ---------------------------------------------------------------------------
# Axe INTER-GENERATIONNEL (replication, graine 22) : branche montante de H1
# Axe INTRA-VIE (graine 21, T_env maximale)        : branche descendante

$runs = @(
  @{tenv="stable";   vvie="nulle";     seed=22; nom="stable_s22"},
  @{tenv="faible";   vvie="nulle";     seed=22; nom="faible_s22"},
  @{tenv="forte";    vvie="nulle";     seed=22; nom="forte_s22"},
  @{tenv="maximale"; vvie="nulle";     seed=22; nom="maximale_s22"},
  @{tenv="maximale"; vvie="lente";     seed=21; nom="vvie_lente_s21"},
  @{tenv="maximale"; vvie="moderee";   seed=21; nom="vvie_moderee_s21"},
  @{tenv="maximale"; vvie="rapide";    seed=21; nom="vvie_rapide_s21"},
  @{tenv="maximale"; vvie="chaotique"; seed=21; nom="vvie_chaotique_s21"}
)

# Refuser de demarrer si un journal existe deja : evolution.py s'arreterait
# run par run, et on ne le verrait qu'au retour.
$existants = $runs | Where-Object { Test-Path "runs/$($_.nom).csv" }
if ($existants) {
    Write-Host "ARRET : ces journaux existent deja :" -ForegroundColor Red
    $existants | ForEach-Object { Write-Host "  runs/$($_.nom).csv" }
    Write-Host "  Renomme-les, deplace-les, ou change les noms dans ce script."
    exit 1
}

# ---------------------------------------------------------------------------
# Lancement, par paquets adaptes au nombre de coeurs
# ---------------------------------------------------------------------------

$max = [math]::Max(1, [math]::Floor([Environment]::ProcessorCount / 2))
Write-Host "$($runs.Count) runs, $max en parallele (sur $([Environment]::ProcessorCount) processeurs logiques)."
Write-Host "Journaux de sortie dans logs\, resultats dans runs\."
Write-Host ""

$debut = Get-Date
foreach ($r in $runs) {
    while (@(Get-Job -State Running).Count -ge $max) { Start-Sleep -Seconds 5 }
    Write-Host "  demarrage : $($r.nom)  (tenv=$($r.tenv), vvie=$($r.vvie), seed=$($r.seed))"
    Start-Job -ScriptBlock {
        param($py, $t, $v, $s, $nom, $dossier)
        Set-Location $dossier
        # Toutes les sorties (y compris les erreurs) vont dans un fichier :
        # sans cela, un run qui echoue le fait silencieusement.
        & $py evolution.py --tenv $t --vvie $v --seed $s `
            --generations 60 --journal "runs/$nom.csv" *> "logs/$nom.log"
    } -ArgumentList $python, $r.tenv, $r.vvie, $r.seed, $r.nom, $PWD.Path | Out-Null
}

Write-Host ""
Write-Host "Tous les runs sont lances. Attente..."
Get-Job | Wait-Job | Out-Null
Get-Job | Remove-Job

# ---------------------------------------------------------------------------
# Bilan
# ---------------------------------------------------------------------------

$duree = (Get-Date) - $debut
Write-Host ""
Write-Host "Termine en $([math]::Round($duree.TotalMinutes)) minutes."
Write-Host ""
foreach ($r in $runs) {
    $csv = "runs/$($r.nom).csv"
    if (Test-Path $csv) {
        # -1 pour l'en-tete
        $n = (Get-Content $csv | Measure-Object -Line).Lines - 1
        if ($n -ge 60) {
            Write-Host ("  OK       {0,-24} {1} generations" -f $r.nom, $n) -ForegroundColor Green
        } else {
            Write-Host ("  PARTIEL  {0,-24} {1} generations" -f $r.nom, $n) -ForegroundColor Yellow
        }
    } else {
        Write-Host ("  ECHEC    {0,-24} voir logs\{0}.log" -f $r.nom) -ForegroundColor Red
    }
}

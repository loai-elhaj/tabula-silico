# Tabula Silico — replications de l'axe INTRA-VIE (graines 22 et 23)
# Usage :  .\lancer_replications.ps1
# ou    :  powershell -ExecutionPolicy Bypass -File .\lancer_replications.ps1

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Verifications prealables
# ---------------------------------------------------------------------------

$python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "ARRET : $python introuvable." -ForegroundColor Red
    exit 1
}

& $python -c "import neat, numpy, pygame" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ARRET : dependances manquantes dans le venv." -ForegroundColor Red
    Write-Host "  .\venv\Scripts\pip.exe install -r requirements.txt"
    exit 1
}

if (-not (Test-Path "runs")) { New-Item -ItemType Directory -Path "runs" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

# ---------------------------------------------------------------------------
# Les runs : 5 niveaux intra-vie x 2 graines, a T_env = maximale
# ---------------------------------------------------------------------------
# T_env est fixe sur "maximale" : la validite des types s'inverse a chaque
# generation, donc aucune preference HEREDITAIRE ne peut jamais etre correcte.
# Seul l'apprentissage peut aider — c'est la condition qui isole proprement
# l'effet de la volatilite INTRA-VIE.

$niveaux = @("nulle", "lente", "moderee", "rapide", "chaotique")
$graines = @(22, 23)

$runs = @()
foreach ($g in $graines) {
    foreach ($n in $niveaux) {
        $runs += @{tenv="maximale"; vvie=$n; seed=$g; nom="vvie_${n}_s${g}"}
    }
}

$existants = $runs | Where-Object { Test-Path "runs/$($_.nom).csv" }
if ($existants) {
    Write-Host "ARRET : ces journaux existent deja :" -ForegroundColor Red
    $existants | ForEach-Object { Write-Host "  runs/$($_.nom).csv" }
    exit 1
}

# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------

$max = [math]::Max(1, [math]::Floor([Environment]::ProcessorCount / 2))
Write-Host "$($runs.Count) runs, $max en parallele (sur $([Environment]::ProcessorCount) processeurs logiques)."
Write-Host ""

$debut = Get-Date
foreach ($r in $runs) {
    while (@(Get-Job -State Running).Count -ge $max) { Start-Sleep -Seconds 5 }
    Write-Host "  demarrage : $($r.nom)"
    Start-Job -ScriptBlock {
        param($py, $t, $v, $s, $nom, $dossier)
        Set-Location $dossier
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

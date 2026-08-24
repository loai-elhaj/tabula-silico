# Tabula Silico — H2 : le cout de l'apprentissage comme force de rappel
# Usage :  .\lancer_h2.ps1
# ou    :  powershell -ExecutionPolicy Bypass -File .\lancer_h2.ps1
#
# HYPOTHESE H2 : a volatilite favorable a la plasticite, augmenter le cout de
# l'apprentissage doit faire refluer la selection vers l'inne (eta decroit).
#
# Condition fixee : T_env = maximale, vvie = nulle.
# C'est la condition ou la plasticite est LE PLUS avantageuse (ecart
# plastique-fige de +0,083, eta = 0,499). Un cout croissant doit donc y
# produire l'effet le plus visible.
#
# CALIBRATION de lambda — les valeurs ne sont pas arbitraires. Mesure sur les
# trois graines de la condition de reference : fitness moyenne F = 234,8,
# cout d'apprentissage realise moyen C = 6,21. lambda est choisi pour que le
# cout represente une fraction cible de la fitness : lambda = fraction x F / C.
#
#   lambda = 0     cout nul        (temoin)
#   lambda = 3.8   cout ~10 %
#   lambda = 9.4   cout ~25 %
#   lambda = 18.9  cout ~50 %

$ErrorActionPreference = "Stop"

$python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "ARRET : $python introuvable." -ForegroundColor Red
    exit 1
}

& $python -c "import neat, numpy, pygame" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ARRET : dependances manquantes dans le venv." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "runs")) { New-Item -ItemType Directory -Path "runs" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

# ---------------------------------------------------------------------------
# Les runs : 4 niveaux de cout x 3 graines
# ---------------------------------------------------------------------------
# Le niveau cout=0 existe deja (runs/vvie_nulle_s2X.csv) : inutile de le
# relancer, il servira de temoin a l'analyse.

$couts = @(
  @{val=3.8;  nom="c10"},
  @{val=9.4;  nom="c25"},
  @{val=18.9; nom="c50"}
)
$graines = @(21, 22, 23)

$runs = @()
foreach ($g in $graines) {
    foreach ($c in $couts) {
        $runs += @{cout=$c.val; seed=$g; nom="h2_$($c.nom)_s$g"}
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
    Write-Host "  demarrage : $($r.nom)  (cout=$($r.cout), seed=$($r.seed))"
    Start-Job -ScriptBlock {
        param($py, $c, $s, $nom, $dossier)
        Set-Location $dossier
        & $py evolution.py --tenv maximale --vvie nulle --cout $c --seed $s `
            --generations 60 --journal "runs/$nom.csv" *> "logs/$nom.log"
    } -ArgumentList $python, $r.cout, $r.seed, $r.nom, $PWD.Path | Out-Null
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
            Write-Host ("  OK       {0,-20} {1} generations" -f $r.nom, $n) -ForegroundColor Green
        } else {
            Write-Host ("  PARTIEL  {0,-20} {1} generations" -f $r.nom, $n) -ForegroundColor Yellow
        }
    } else {
        Write-Host ("  ECHEC    {0,-20} voir logs\{0}.log" -f $r.nom) -ForegroundColor Red
    }
}

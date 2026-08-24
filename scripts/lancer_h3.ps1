# Tabula Silico — H3 : populations evoluees pour les lesions in silico
# Usage :  powershell -ExecutionPolicy Bypass -File .\lancer_h3.ps1
#
# Les lesions se pratiquent sur une population EVOLUEE. Or les runs precedents
# ne sauvegardaient pas leur population finale — il faut donc les refaire une
# fois, avec l'option --population.
#
# Trois conditions choisies pour couvrir les trois regimes identifies :
#   stable        l'inne suffit          -> l'acquis devrait apporter peu
#   maximale      seul l'acquis aide     -> l'acquis devrait tout apporter
#   chaotique     rien ne peut aider     -> ni l'un ni l'autre
#
# C'est la comparaison entre ces trois regimes qui teste H3 : la contribution
# respective de l'inne et de l'acquis doit DEPENDRE de l'environnement.

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

foreach ($d in @("runs", "logs", "pops")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

# ---------------------------------------------------------------------------

$conditions = @(
  @{tenv="stable";   vvie="nulle";     nom="h3_stable"},
  @{tenv="maximale"; vvie="nulle";     nom="h3_maximale"},
  @{tenv="maximale"; vvie="chaotique"; nom="h3_chaotique"}
)
$graines = @(21, 22, 23)

$runs = @()
foreach ($g in $graines) {
    foreach ($c in $conditions) {
        $runs += @{tenv=$c.tenv; vvie=$c.vvie; seed=$g; nom="$($c.nom)_s$g"}
    }
}

$existants = $runs | Where-Object { Test-Path "pops/$($_.nom).pkl" }
if ($existants) {
    Write-Host "ARRET : ces populations existent deja :" -ForegroundColor Red
    $existants | ForEach-Object { Write-Host "  pops/$($_.nom).pkl" }
    exit 1
}

$max = [math]::Max(1, [math]::Floor([Environment]::ProcessorCount / 2))
Write-Host "$($runs.Count) runs, $max en parallele."
Write-Host ""

$debut = Get-Date
foreach ($r in $runs) {
    while (@(Get-Job -State Running).Count -ge $max) { Start-Sleep -Seconds 5 }
    Write-Host "  demarrage : $($r.nom)"
    Start-Job -ScriptBlock {
        param($py, $t, $v, $s, $nom, $dossier)
        Set-Location $dossier
        & $py evolution.py --tenv $t --vvie $v --seed $s --generations 60 `
            --journal "runs/$nom.csv" --population "pops/$nom.pkl" `
            *> "logs/$nom.log"
    } -ArgumentList $python, $r.tenv, $r.vvie, $r.seed, $r.nom, $PWD.Path | Out-Null
}

Write-Host ""
Write-Host "Attente..."
Get-Job | Wait-Job | Out-Null
Get-Job | Remove-Job

$duree = (Get-Date) - $debut
Write-Host ""
Write-Host "Runs termines en $([math]::Round($duree.TotalMinutes)) minutes."
Write-Host ""

# ---------------------------------------------------------------------------
# Lesions, enchainees automatiquement
# ---------------------------------------------------------------------------

$ok = $true
foreach ($r in $runs) {
    if (-not (Test-Path "pops/$($r.nom).pkl")) {
        Write-Host ("  ECHEC  {0,-20} voir logs\{0}.log" -f $r.nom) -ForegroundColor Red
        $ok = $false
    }
}
if (-not $ok) {
    Write-Host "Certaines populations manquent, lesions non lancees." -ForegroundColor Red
    exit 1
}

Write-Host "Lesions in silico :"
Write-Host ""
foreach ($r in $runs) {
    & $python lesions.py "pops/$($r.nom).pkl" | Tee-Object -FilePath "logs/lesions_$($r.nom).txt"
    Write-Host ""
}
Write-Host "Resultats des lesions egalement enregistres dans logs\lesions_*.txt"

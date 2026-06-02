cran_repo <- "https://cloud.r-project.org"
args <- commandArgs(trailingOnly = TRUE)

user_lib <- if (length(args) >= 1 && nzchar(args[[1]])) args[[1]] else Sys.getenv("R_LIBS_USER", unset = "")
if (!nzchar(user_lib)) {
  if (.Platform$OS.type == "windows") {
    local_app <- Sys.getenv("LOCALAPPDATA", unset = Sys.getenv("USERPROFILE"))
    r_minor <- paste(R.version$major, strsplit(R.version$minor, "\\.")[[1]][1], sep = ".")
    user_lib <- file.path(local_app, "R", "win-library", r_minor)
  } else {
    r_minor <- paste(R.version$major, strsplit(R.version$minor, "\\.")[[1]][1], sep = ".")
    user_lib <- file.path(Sys.getenv("HOME"), "R", r_minor, "library")
  }
}
dir.create(user_lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(unique(c(user_lib, .libPaths())))
cat("Using R library paths:\n")
cat(paste(.libPaths(), collapse = "\n"), "\n")

install_if_missing_cran <- function(pkgs) {
  missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0) {
    install.packages(missing, repos = cran_repo)
  }
}

install_if_missing_bioc <- function(pkgs) {
  missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) == 0) return(invisible())
  if (!requireNamespace("BiocManager", quietly = TRUE)) {
    install.packages("BiocManager", repos = cran_repo)
  }
  BiocManager::install(missing, ask = FALSE, update = FALSE)
}

install_if_missing_cran(c("remotes"))
install_if_missing_bioc(c("GSVA", "GSEABase", "Biobase"))

if (!requireNamespace("tidyestimate", quietly = TRUE)) {
  install.packages("tidyestimate", repos = cran_repo)
}

if (!requireNamespace("MCPcounter", quietly = TRUE)) {
  try(install.packages("MCPcounter", repos = cran_repo), silent = TRUE)
}
if (!requireNamespace("MCPcounter", quietly = TRUE)) {
  try(remotes::install_github("ebecht/MCPcounter", ref = "master", subdir = "Source"), silent = TRUE)
}

if (!requireNamespace("xCell", quietly = TRUE)) {
  try(BiocManager::install("xCell", ask = FALSE, update = FALSE), silent = TRUE)
}
if (!requireNamespace("xCell", quietly = TRUE)) {
  try(remotes::install_github("dviraran/xCell"), silent = TRUE)
}

required <- c("GSVA", "tidyestimate")
missing_required <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_required) > 0) {
  stop("Failed to install required R package(s): ", paste(missing_required, collapse = ", "), call. = FALSE)
}
optional <- c("MCPcounter", "xCell")
missing_optional <- optional[!vapply(optional, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_optional) > 0) {
  warning("Optional immune scoring package(s) unavailable: ", paste(missing_optional, collapse = ", "),
          ". Immune cell features will use ssGSEA signatures when those optional methods are unavailable.")
}
cat("R package installation complete.\n")

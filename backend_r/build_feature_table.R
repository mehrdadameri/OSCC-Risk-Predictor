#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE)
set.seed(20260526)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 7) {
  stop(
    "Usage: Rscript build_feature_table.R <expression_csv> <output_dir> <age> <sex_male> <stage_late> <model_dir> <hallmark_gmt>",
    call. = FALSE
  )
}

expression_csv <- normalizePath(args[[1]], mustWork = TRUE)
output_dir <- args[[2]]
age_value <- as.numeric(args[[3]])
sex_male_value <- as.numeric(args[[4]])
stage_late_value <- as.numeric(args[[5]])
model_dir <- normalizePath(args[[6]], mustWork = TRUE)
gmt_path <- normalizePath(args[[7]], mustWork = TRUE)

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

user_lib <- Sys.getenv("OSCC_R_LIBRARY", unset = "")
if (!nzchar(user_lib)) {
  user_lib <- Sys.getenv("R_LIBS_USER", unset = "")
}
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
if (dir.exists(user_lib)) {
  .libPaths(unique(c(user_lib, .libPaths())))
}

required_features_path <- file.path(model_dir, "required_model_features.csv")
panel_path <- file.path(model_dir, "biomarker_panel.csv")
feature_table_out <- file.path(output_dir, "prepared_feature_table.csv")
audit_out <- file.path(output_dir, "preprocessing_audit.csv")

required_features <- read.csv(required_features_path, check.names = FALSE)$feature
panel_symbols <- toupper(read.csv(panel_path, check.names = FALSE)$gene_symbol)

required_packages <- function(pkgs) {
  missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0) {
    stop("Missing required R package(s): ", paste(missing, collapse = ", "), call. = FALSE)
  }
}

optional_package <- function(pkg) {
  requireNamespace(pkg, quietly = TRUE)
}

write_csv <- function(x, path, row.names = FALSE) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  write.csv(x, path, row.names = row.names, quote = TRUE)
  message("Wrote: ", path)
}

read_expression_upload <- function(path) {
  dat <- read.csv(path, check.names = FALSE)
  if (nrow(dat) == 0 || ncol(dat) < 2) {
    stop("Expression matrix must contain a gene-symbol column and at least one sample column.", call. = FALSE)
  }
  gene_candidates <- c("gene_symbol", "hgnc_symbol", "symbol", "gene", "genes", "Gene", "SYMBOL", "HGNC")
  gene_col <- intersect(gene_candidates, colnames(dat))
  gene_col <- if (length(gene_col) > 0) gene_col[[1]] else colnames(dat)[[1]]
  genes <- toupper(trimws(as.character(dat[[gene_col]])))
  keep <- !is.na(genes) & genes != "" & genes != "NAN"
  dat <- dat[keep, , drop = FALSE]
  genes <- genes[keep]
  sample_cols <- setdiff(colnames(dat), gene_col)
  expr <- as.data.frame(lapply(dat[, sample_cols, drop = FALSE], function(v) as.numeric(as.character(v))), check.names = FALSE)
  expr$gene_symbol <- genes
  expr <- stats::aggregate(. ~ gene_symbol, data = expr, FUN = function(x) stats::median(x, na.rm = TRUE), na.action = NULL)
  rownames(expr) <- expr$gene_symbol
  expr$gene_symbol <- NULL
  mat <- as.matrix(expr)
  storage.mode(mat) <- "numeric"
  mat[!is.finite(mat)] <- NA_real_
  for (j in seq_len(ncol(mat))) {
    if (all(is.na(mat[, j]))) {
      mat[, j] <- 0
    } else {
      mat[is.na(mat[, j]), j] <- stats::median(mat[, j], na.rm = TRUE)
    }
  }
  meta <- data.frame(
    SampleID = colnames(mat),
    dataset = "uploaded",
    survival_time = NA_real_,
    event = NA_real_,
    stringsAsFactors = FALSE
  )
  list(meta = meta, expr_samples_by_genes = t(mat))
}

expr_for_gene_set_methods <- function(expr_samples_by_genes) {
  expr <- t(expr_samples_by_genes)
  rownames(expr) <- make.unique(toupper(rownames(expr)))
  colnames(expr) <- rownames(expr_samples_by_genes)
  expr
}

run_gsva_method <- function(expr_genes_by_samples, gene_sets, method) {
  method <- match.arg(method, c("ssgsea", "gsva"))
  if (method == "ssgsea" && exists("ssgseaParam", where = asNamespace("GSVA"), inherits = FALSE)) {
    param <- GSVA::ssgseaParam(exprData = expr_genes_by_samples, geneSets = gene_sets, normalize = TRUE)
    return(GSVA::gsva(param, verbose = FALSE))
  }
  if (method == "gsva" && exists("gsvaParam", where = asNamespace("GSVA"), inherits = FALSE)) {
    param <- GSVA::gsvaParam(exprData = expr_genes_by_samples, geneSets = gene_sets, kcdf = "Gaussian")
    return(GSVA::gsva(param, verbose = FALSE))
  }
  GSVA::gsva(
    expr = expr_genes_by_samples,
    gset.idx.list = gene_sets,
    method = method,
    kcdf = "Gaussian",
    abs.ranking = FALSE,
    verbose = FALSE
  )
}

get_hallmark_gene_sets <- function(expression_genes) {
  if (!file.exists(gmt_path)) stop("Hallmark GMT file not found: ", gmt_path, call. = FALSE)
  lines <- readLines(gmt_path)
  gene_sets <- list()
  audit_rows <- list()
  for (line in lines) {
    parts <- strsplit(line, "\t")[[1]]
    set_name <- parts[1]
    genes <- toupper(parts[-(1:2)])
    genes <- sort(unique(intersect(genes, expression_genes)))
    gene_sets[[set_name]] <- genes
    audit_rows[[length(audit_rows) + 1]] <- data.frame(
      step = "pathway_overlap",
      item = set_name,
      status = "checked",
      detail = paste0(length(genes), " overlapping genes"),
      stringsAsFactors = FALSE
    )
  }
  audit <- do.call(rbind, audit_rows)
  gene_sets <- gene_sets[vapply(gene_sets, length, integer(1)) >= 10]
  list(gene_sets = gene_sets, audit = audit)
}

score_to_samples_by_pathways <- function(scores, meta, prefix = "") {
  out <- as.data.frame(t(scores), check.names = FALSE)
  if (nzchar(prefix)) colnames(out) <- paste0(prefix, colnames(out))
  out$SampleID <- rownames(out)
  merge(meta[, c("SampleID", "dataset", "survival_time", "event")], out, by = "SampleID", all.x = TRUE, sort = FALSE)
}

immune_signature_sets <- list(
  CD8_T_cell = c("CD8A", "CD8B", "TRAC", "CTSW", "TRAT1", "LTB"),
  CD4_T_cell = c("CD4", "IL7R", "TCF7", "LTB", "TRAT1", "MAL"),
  Treg = c("FOXP3", "IL2RA", "IKZF2", "CTLA4", "TIGIT", "CCR8", "LAIR2"),
  Exhausted_T_cell = c("PDCD1", "LAG3", "HAVCR2", "TIGIT", "CTLA4", "CXCL13", "LAYN", "GZMK"),
  Cytotoxic_T_NK = c("NKG7", "GNLY", "PRF1", "GZMB", "FGFBP2", "KLRD1", "CTSW", "CCL5"),
  B_cell = c("MS4A1", "CD79A", "CD79B", "CD19", "CD22", "BANK1", "FCRL2", "PAX5"),
  Plasma_cell = c("MZB1", "TNFRSF17", "CD38", "IGKC", "SDC1"),
  Macrophage_M1_like = c("IL1B", "FCN1", "CXCL9", "CXCL10", "HLA-DRA", "STAT1"),
  Macrophage_M2_TAM_like = c("CD163", "MRC1", "MSR1", "CCL18", "C1QA", "C1QB", "SPP1"),
  Pan_macrophage = c("CSF1R", "LST1", "FCER1G", "TYROBP", "C1QA", "C1QB", "AIF1"),
  Dendritic_cell = c("FCER1A", "CD1C", "CLEC10A", "IRF8", "LAMP3", "HLA-DRA"),
  Neutrophil = c("FCGR3B", "CEACAM3", "CXCR1", "CXCR2", "S100A8", "S100A9", "VNN3"),
  Mast_cell = c("TPSAB1", "MS4A2", "CPA3", "HDC", "KIT", "HPGDS"),
  NK_cell = c("NCR1", "KLRD1", "KLRF1", "SH2D1B", "CD160", "KIR2DL4", "KIR3DL1", "PTGDR"),
  CAF = c("COL1A1", "COL1A2", "COL3A1", "COL6A1", "DCN", "LUM", "FAP", "PDPN"),
  Endothelial = c("PECAM1", "CDH5", "KDR", "EMCN", "ESAM", "ROBO4", "VWF", "CLEC14A")
)

ssgsea_immune_scores <- function(expr_genes_by_samples, meta, label) {
  if (!optional_package("GSVA")) return(NULL)
  audit <- data.frame()
  sets <- lapply(immune_signature_sets, function(g) intersect(g, rownames(expr_genes_by_samples)))
  for (nm in names(sets)) {
    audit <- rbind(audit, data.frame(
      step = "immune_signature_overlap",
      item = nm,
      status = "checked",
      detail = paste0(length(sets[[nm]]), "/", length(immune_signature_sets[[nm]]), " genes: ", paste(sets[[nm]], collapse = ";")),
      stringsAsFactors = FALSE
    ))
  }
  sets <- sets[vapply(sets, length, integer(1)) >= 3]
  if (length(sets) == 0) return(list(scores = NULL, audit = audit))
  if (exists("ssgseaParam", where = asNamespace("GSVA"), inherits = FALSE)) {
    param <- GSVA::ssgseaParam(exprData = expr_genes_by_samples, geneSets = sets, normalize = TRUE)
    score <- GSVA::gsva(param, verbose = FALSE)
  } else {
    score <- GSVA::gsva(expr_genes_by_samples, sets, method = "ssgsea", kcdf = "Gaussian", verbose = FALSE)
  }
  out <- as.data.frame(t(score), check.names = FALSE)
  colnames(out) <- paste0("immune_ssgsea_", colnames(out), "_score")
  out$SampleID <- rownames(out)
  out <- merge(meta[, c("SampleID", "dataset", "survival_time", "event"), drop = FALSE], out, by = "SampleID", all.x = TRUE, sort = FALSE)
  list(scores = out, audit = audit)
}

pick_score_column <- function(df, patterns) {
  nms <- tolower(gsub("[^a-zA-Z0-9]+", "_", colnames(df)))
  for (pattern in patterns) {
    hit <- grep(pattern, nms)
    if (length(hit) > 0) return(colnames(df)[hit[1]])
  }
  NA_character_
}

normalize_tidyestimate_scores <- function(scores, meta) {
  out <- as.data.frame(scores, check.names = FALSE)
  sample_col <- pick_score_column(out, c("^sample$", "sample_id", "tumou?r", "^id$"))
  if (!is.na(sample_col)) {
    sample_id <- as.character(out[[sample_col]])
  } else if (!is.null(rownames(out)) && all(nzchar(rownames(out)))) {
    sample_id <- rownames(out)
  } else {
    stop("Could not identify sample IDs in tidyestimate output.", call. = FALSE)
  }
  stromal_col <- pick_score_column(out, c("^stromal$", "stromal_score", "^stroma$", "stroma_score"))
  immune_col <- pick_score_column(out, c("^immune$", "immune_score"))
  estimate_col <- pick_score_column(out, c("^estimate$", "estimate_score"))
  purity_col <- pick_score_column(out, c("purity_predicted", "purity_score", "^purity$", "tumou?r_purity"))
  normalized <- data.frame(SampleID = sample_id, stringsAsFactors = FALSE)
  normalized$stromal_score <- if (!is.na(stromal_col)) as.numeric(out[[stromal_col]]) else NA_real_
  normalized$immune_score <- if (!is.na(immune_col)) as.numeric(out[[immune_col]]) else NA_real_
  normalized$estimate_score <- if (!is.na(estimate_col)) as.numeric(out[[estimate_col]]) else NA_real_
  normalized$tumor_purity <- if (!is.na(purity_col)) as.numeric(out[[purity_col]]) else NA_real_
  merge(meta[, c("SampleID", "dataset", "survival_time", "event"), drop = FALSE],
        normalized, by = "SampleID", all.x = TRUE, sort = FALSE)
}

run_tidyestimate <- function(expr_genes_by_samples, meta, label) {
  expr <- expr_genes_by_samples[!duplicated(rownames(expr_genes_by_samples)), , drop = FALSE]
  estimate_input <- data.frame(hgnc_symbol = rownames(expr), expr, check.names = FALSE)
  filtered <- tidyestimate::filter_common_genes(
    estimate_input,
    id = "hgnc_symbol",
    tidy = TRUE,
    tell_missing = FALSE,
    find_alias = TRUE
  )
  scores <- tidyestimate::estimate_score(filtered, is_affymetrix = TRUE)
  out <- normalize_tidyestimate_scores(scores, meta)
  attr(out, "tidyestimate_input_genes") <- nrow(estimate_input)
  attr(out, "tidyestimate_filtered_genes") <- nrow(filtered)
  out
}

run_mcpcounter <- function(expr_genes_by_samples, meta) {
  if (!optional_package("MCPcounter")) return(NULL)
  tryCatch({
    score <- MCPcounter::MCPcounter.estimate(expr_genes_by_samples, featuresType = "HUGO_symbols")
    out <- as.data.frame(t(score), check.names = FALSE)
    out$SampleID <- rownames(out)
    colnames(out) <- make.names(colnames(out))
    colnames(out) <- paste0("mcpcounter_", colnames(out))
    colnames(out)[colnames(out) == "mcpcounter_SampleID"] <- "SampleID"
    merge(meta[, c("SampleID", "dataset", "survival_time", "event"), drop = FALSE], out, by = "SampleID", all.x = TRUE, sort = FALSE)
  }, error = function(e) {
    warning("MCPcounter failed: ", conditionMessage(e))
    NULL
  })
}

run_xcell <- function(expr_genes_by_samples, meta) {
  if (!optional_package("xCell")) return(NULL)
  tryCatch({
    data("xCell.data", package = "xCell")
    score <- xCell::xCellAnalysis(expr_genes_by_samples)
    out <- as.data.frame(t(score), check.names = FALSE)
    out$SampleID <- rownames(out)
    colnames(out) <- make.names(colnames(out))
    colnames(out) <- paste0("xcell_", colnames(out))
    colnames(out)[colnames(out) == "xcell_SampleID"] <- "SampleID"
    merge(meta[, c("SampleID", "dataset", "survival_time", "event"), drop = FALSE], out, by = "SampleID", all.x = TRUE, sort = FALSE)
  }, error = function(e) {
    warning("xCell failed: ", conditionMessage(e))
    NULL
  })
}

immune_cell_method_mapping <- list(
  CD8_T_cell              = list(xcell = c("xcell_CD8..T.cells"),            mcp = c("mcpcounter_CD8.T.cells")),
  CD4_T_cell              = list(xcell = c("xcell_CD4..T.cells"),            mcp = c("mcpcounter_T.cells")),
  Treg                    = list(xcell = c("xcell_Tregs"),                   mcp = character(0)),
  Exhausted_T_cell        = list(xcell = character(0),                       mcp = character(0)),
  Cytotoxic_T_NK          = list(xcell = character(0),                       mcp = c("mcpcounter_Cytotoxic.lymphocytes")),
  B_cell                  = list(xcell = c("xcell_B.cells"),                 mcp = c("mcpcounter_B.lineage")),
  Plasma_cell             = list(xcell = c("xcell_Plasma.cells"),            mcp = character(0)),
  Macrophage_M1_like      = list(xcell = c("xcell_Macrophages.M1"),          mcp = character(0)),
  Macrophage_M2_TAM_like  = list(xcell = c("xcell_Macrophages.M2"),          mcp = character(0)),
  Pan_macrophage          = list(xcell = c("xcell_Macrophages"),             mcp = c("mcpcounter_Monocytic.lineage")),
  Dendritic_cell          = list(xcell = c("xcell_DC"),                      mcp = c("mcpcounter_Myeloid.dendritic.cells")),
  Neutrophil              = list(xcell = c("xcell_Neutrophils"),             mcp = c("mcpcounter_Neutrophils")),
  Mast_cell               = list(xcell = c("xcell_Mast.cells"),              mcp = character(0)),
  NK_cell                 = list(xcell = c("xcell_NK.cells"),                mcp = c("mcpcounter_NK.cells")),
  CAF                     = list(xcell = c("xcell_Fibroblasts"),             mcp = c("mcpcounter_Fibroblasts")),
  Endothelial             = list(xcell = c("xcell_Endothelial.cells"),       mcp = c("mcpcounter_Endothelial.cells"))
)

pick_feature <- function(dfs, candidates) {
  for (candidate in candidates) {
    for (df in dfs) {
      if (!is.null(df) && candidate %in% colnames(df)) return(df[[candidate]])
    }
  }
  rep(NA_real_, nrow(dfs[[1]]))
}

build_compact_immune <- function(meta, tidyestimate_df, mcp_df, xcell_df, ssgsea_df) {
  dfs <- list(meta[, c("SampleID", "dataset", "survival_time", "event"), drop = FALSE], tidyestimate_df, mcp_df, xcell_df, ssgsea_df)
  compact <- meta[, c("SampleID", "dataset", "survival_time", "event"), drop = FALSE]
  compact$immune_score <- pick_feature(dfs, c("immune_score"))
  compact$stromal_score <- pick_feature(dfs, c("stromal_score"))
  compact$estimate_score <- pick_feature(dfs, c("estimate_score"))
  compact$tumor_purity <- pick_feature(dfs, c("tumor_purity"))
  for (ct in names(immune_cell_method_mapping)) {
    candidates <- c(
      immune_cell_method_mapping[[ct]]$xcell,
      immune_cell_method_mapping[[ct]]$mcp,
      paste0("immune_ssgsea_", ct, "_score")
    )
    compact[[paste0(ct, "_score")]] <- pick_feature(dfs, candidates)
  }
  compact
}

main <- function() {
  message("__PHASE__:Loading expression matrix")
  required_packages(c("GSVA", "tidyestimate"))
  obj <- read_expression_upload(expression_csv)
  rownames(obj$expr_samples_by_genes) <- obj$meta$SampleID
  expr <- expr_for_gene_set_methods(obj$expr_samples_by_genes)
  expression_genes <- rownames(expr)

  audit <- data.frame(
    step = "input",
    item = "expression_matrix",
    status = "loaded",
    detail = paste0(nrow(obj$meta), " sample(s), ", nrow(expr), " unique HGNC gene(s)"),
    stringsAsFactors = FALSE
  )

  message("__PHASE__:Mapping Hallmark gene sets")
  hallmark <- get_hallmark_gene_sets(expression_genes)
  audit <- rbind(audit, hallmark$audit)
  if (length(hallmark$gene_sets) < 40) {
    warning("Fewer than 40 Hallmark gene sets have >=10 overlapping genes. Check uploaded HGNC symbols.")
  }
  message("__PHASE__:Calculating ssGSEA pathway scores")
  ssgsea_scores <- run_gsva_method(expr, hallmark$gene_sets, "ssgsea")
  ssgsea <- score_to_samples_by_pathways(ssgsea_scores, obj$meta, prefix = "ssgsea_")

  message("__PHASE__:Calculating TME scores")
  immune_ssgsea <- ssgsea_immune_scores(expr, obj$meta, "uploaded")
  tidyestimate_df <- run_tidyestimate(expr, obj$meta, "uploaded")
  mcp_df <- run_mcpcounter(expr, obj$meta)
  xcell_df <- run_xcell(expr, obj$meta)
  immune <- build_compact_immune(obj$meta, tidyestimate_df, mcp_df, xcell_df, immune_ssgsea$scores)
  audit <- rbind(audit, immune_ssgsea$audit)
  audit <- rbind(audit, data.frame(
    step = "immune_methods",
    item = "method_availability",
    status = "checked",
    detail = paste0(
      "tidyestimate=TRUE; GSVA_immune=", !is.null(immune_ssgsea$scores),
      "; MCPcounter=", !is.null(mcp_df),
      "; xCell=", !is.null(xcell_df)
    ),
    stringsAsFactors = FALSE
  ))

  message("__PHASE__:Subsetting biomarker panel")
  expr_df <- as.data.frame(obj$expr_samples_by_genes[, intersect(panel_symbols, colnames(obj$expr_samples_by_genes)), drop = FALSE], check.names = FALSE)
  missing_panel <- setdiff(panel_symbols, colnames(expr_df))
  if (length(missing_panel) > 0) {
    stop("Uploaded expression matrix is missing required 43-gene panel symbol(s): ", paste(missing_panel, collapse = ", "), call. = FALSE)
  }
  colnames(expr_df) <- paste0("gene_", colnames(expr_df))
  expr_df$SampleID <- rownames(obj$expr_samples_by_genes)
  expr_df <- merge(obj$meta, expr_df, by = "SampleID", sort = FALSE)

  clinical_block <- obj$meta
  clinical_block$clinical_stage_late <- stage_late_value
  clinical_block$clinical_age_continuous <- age_value
  clinical_block$clinical_sex_male <- sex_male_value

  immune_features <- setdiff(colnames(immune), c("SampleID", "dataset", "survival_time", "event"))
  colnames(immune)[match(immune_features, colnames(immune))] <- paste0("immune_", immune_features)

  message("__PHASE__:Assembling final feature table")
  aligned <- Reduce(function(x, y) merge(x, y, by = c("SampleID", "dataset", "survival_time", "event"), all = FALSE, sort = FALSE),
                    list(expr_df, ssgsea, immune, clinical_block))

  missing_features <- setdiff(required_features, colnames(aligned))
  if (length(missing_features) > 0) {
    stop("R preprocessing did not generate required model feature(s): ", paste(missing_features, collapse = ", "), call. = FALSE)
  }

  feature_table <- aligned[, c("SampleID", required_features), drop = FALSE]
  nonfinite_features <- required_features[vapply(required_features, function(feature) {
    any(!is.finite(as.numeric(feature_table[[feature]])))
  }, logical(1))]
  if (length(nonfinite_features) > 0) {
    stop("R preprocessing generated non-finite required model feature(s): ", paste(nonfinite_features, collapse = ", "), call. = FALSE)
  }
  write_csv(feature_table, feature_table_out)
  write_csv(audit, audit_out)
  message("Feature preparation complete.")
}

main()

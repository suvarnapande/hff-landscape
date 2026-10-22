# theme_hee.R — one place for palette, scales and theme.
#
# PRINT-FIRST, DELIBERATELY LIGHT-ONLY. These figures are for a journal, so there is no
# dark mode: the surface is paper. Every other rule from the house data-viz method still
# holds — categorical hues assigned in fixed order and never cycled, one hue light-to-dark
# for magnitude, two hues plus a neutral for polarity, recessive grid, thin marks, a
# legend whenever there are two or more series.
#
# THE PALETTE IS VALIDATED, NOT CHOSEN BY EYE. The categorical order below passes the
# six checks (lightness band, chroma floor, CVD separation, normal-vision floor,
# contrast) on the light surface. The first THREE slots additionally clear the
# all-pairs gate, which is what scatter, choropleth and small-multiple forms need —
# so any figure of those kinds uses at most three colours and folds the rest into
# "Other" or facets. Re-validate with the house validator if you change a hex.
#
# Three of the light-mode hues sit below 3:1 against paper (aqua, yellow, magenta).
# Where they carry meaning the figure ships direct labels — the relief rule.

suppressPackageStartupMessages({
  library(ggplot2); library(scales); library(grid); library(ggtext)
})

# ---- slots ---------------------------------------------------------------
hee_cat <- c(
  blue    = "#2a78d6",
  orange  = "#eb6834",
  aqua    = "#1baf7a",
  yellow  = "#eda100",
  magenta = "#e87ba4",
  green   = "#008300",
  violet  = "#4a3aa7",
  red     = "#e34948"
)
# all-pairs safe subset, for choropleth / scatter / small multiples
hee_cat3 <- unname(hee_cat[1:3])

# one hue, light -> dark, for magnitude
hee_seq <- c("#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
             "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
             "#184f95", "#104281", "#0d366b")
# ordinal ramps must stay >= 2:1 against paper, so start no lighter than step 250
hee_ord <- hee_seq[4:13]
# polarity: warm/cool poles, neutral gray midpoint
hee_div <- c(low = "#1c5cab", mid = "#f0efec", high = "#d03b3b")

hee_ink   <- list(primary = "#0b0b0b", secondary = "#52514e", muted = "#8a8983",
                  grid = "#e6e5e1", surface = "#ffffff")

# Fixed, meaning-bearing assignments. Colour follows the entity, so filtering a
# figure never repaints the survivors.
pal_eval <- c(
  "Cost-utility"       = hee_cat[["blue"]],
  "Cost-effectiveness" = hee_cat[["orange"]],
  "Cost-consequence"   = hee_cat[["aqua"]],
  "Cost-benefit"       = hee_cat[["yellow"]],
  "Cost-minimisation"  = hee_cat[["magenta"]],
  "Budget impact"      = hee_cat[["violet"]],
  "Cost of illness"    = hee_cat[["green"]],
  "None"               = hee_ink$muted
)
pal_income <- c(
  "High income"         = hee_cat[["blue"]],
  "Low & middle income" = hee_cat[["orange"]],
  "Mixed"               = hee_cat[["aqua"]],
  "Not reported"        = hee_ink$muted
)
pal_design <- c(
  "RCT"                           = hee_cat[["blue"]],
  "Quasi-experimental"            = hee_cat[["orange"]],
  "Observational"                 = hee_cat[["aqua"]],
  "Literature/registry synthesis" = hee_cat[["yellow"]],
  "Review"                        = hee_cat[["magenta"]],
  "Qualitative"                   = hee_cat[["violet"]],
  "Other"                         = hee_ink$muted
)

# ---- theme ---------------------------------------------------------------
theme_hee <- function(base_size = 9, grid = "y") {
  th <- theme_minimal(base_size = base_size, base_family = "sans") +
    theme(
      plot.title.position = "plot",
      plot.caption.position = "plot",
      plot.title    = element_text(face = "bold", size = rel(1.25),
                                   colour = hee_ink$primary, margin = margin(b = 3)),
      # Subtitle and caption are TEXTBOXES, not plain text, for two reasons that both
      # showed up on first render: a caption written as one sentence ran off the right
      # edge of the plot, and a subtitle written across several source lines kept the
      # source indentation as literal leading spaces. A textbox re-flows to the plot
      # width and treats the newline as ordinary whitespace, so both are fixed at the
      # theme rather than by hand-hyphenating fifteen strings.
      plot.subtitle = ggtext::element_textbox_simple(
                        size = rel(1.0), colour = hee_ink$secondary,
                        margin = margin(b = 10), lineheight = 1.3),
      # SECOND TRAP: a plot.subtitle textbox that wraps to two lines does not always
      # reserve its own height, and its first line can then be drawn on top of the title.
      # The journal figures in hee-paper.qmd carry NO subtitle for that reason and because
      # a journal figure has a title and a legend and nothing between them. If you do use
      # a subtitle, keep it to one line and check the render.
      #
      # TRAP: subtitle and caption are parsed by gridtext, which supports only a small
      # tag set. **bold**, *italic* and <br> are fine; a markdown CODE SPAN is not --
      # backticks become <code> and gridtext aborts the whole render with
      # "encountered a tag that isn't supported yet". Never put backticks in a title,
      # subtitle or caption; name the column in plain words instead.
      plot.caption  = ggtext::element_textbox_simple(
                        size = rel(0.82), colour = hee_ink$muted, hjust = 0,
                        margin = margin(t = 10), lineheight = 1.25),
      axis.title    = element_text(size = rel(0.92), colour = hee_ink$secondary),
      axis.text     = element_text(size = rel(0.88), colour = hee_ink$secondary),
      axis.ticks    = element_blank(),
      # recessive grid: hairline, one direction only
      panel.grid.major = element_line(colour = hee_ink$grid, linewidth = 0.3),
      panel.grid.minor = element_blank(),
      legend.position  = "top",
      legend.justification = "left",
      legend.title     = element_blank(),
      legend.text      = element_text(size = rel(0.88), colour = hee_ink$secondary),
      legend.key.size  = unit(9, "pt"),
      legend.margin    = margin(b = 2),
      strip.text       = element_text(face = "bold", size = rel(0.92),
                                      colour = hee_ink$primary, hjust = 0),
      plot.background  = element_rect(fill = hee_ink$surface, colour = NA),
      panel.background = element_rect(fill = hee_ink$surface, colour = NA),
      plot.margin      = margin(12, 14, 10, 12)
    )
  if (grid == "y") th <- th + theme(panel.grid.major.x = element_blank())
  if (grid == "x") th <- th + theme(panel.grid.major.y = element_blank())
  if (grid == "none") th <- th + theme(panel.grid.major = element_blank())
  th
}

# 2026 is a partial year in this corpus. Any time series must say so rather than
# letting the reader infer a collapse in the literature.
PARTIAL_YEAR <- 2026L
# Two notes, because the two honest treatments are different. An incomplete year in a
# STACKED AREA reads as a collapse no matter how it is annotated, so those figures drop
# it. A single line can carry it as a hollow point without misleading anyone.
partial_year_excluded <- paste0(
  PARTIAL_YEAR, " is excluded: the search ran mid-year, so its count is incomplete and ",
  "would read as a fall in the literature rather than a truncated series."
)
partial_year_hollow <- paste0(
  "The hollow final point is ", PARTIAL_YEAR, ", an incomplete year; it is plotted ",
  "because a proportion is not distorted by a partial count, but it carries fewer studies."
)

# Counting rule, stated once so every caption can point at it.
denom_note <- list(
  studies   = "Denominator: 44,941 included studies with an extractable abstract.",
  pairs     = paste0("Denominator: study-country pairs, not studies — 2,714 studies ",
                     "name more than one country or a supranational region, so ",
                     "columns sum to more than the study total."),
  outcomes  = paste0("Denominator: 104,217 outcome mentions across 37,678 studies ",
                     "(mean 2.77 each), assigned to families by ordered pattern ",
                     "matching; 23.3% remain specialty-specific and unclassified.")
)

fmt_k <- function(x) label_number(scale_cut = cut_short_scale())(x)

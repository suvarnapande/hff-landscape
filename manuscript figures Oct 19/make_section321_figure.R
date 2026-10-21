# make_section321_figure.R — figure for manuscript section 3.2.1,
# "Research on health financing functions is large and growing fast".
#
# Every number comes straight from the raw dataset (docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv),
# and they match the text: 53,411 studies; 3,611 reviews of studies, so 49,800 (93%) empirical;
# the four designs named in the text (11,036 / 8,284 / 7,090 / 6,235); 29,190 (55%) in 2019 or later.
#
#   fig_section321_size_and_growth   headline numbers, A: studies per year, B: study designs
#
# From this folder:
#   Rscript make_section321_figure.R

.libPaths(c("_rlib", .libPaths()))
source("theme_hee.R")  # copy of docs/theme_hee.R
suppressPackageStartupMessages(library(patchwork))

W_IN <- 7.2  # full journal page width (183 mm)
save_fig <- function(p, name, h) {
  ggsave(paste0(name, ".png"), p, width = W_IN, height = h, dpi = 300, device = ragg::agg_png, bg = "white")
  ggsave(paste0(name, ".pdf"), p, width = W_IN, height = h, device = cairo_pdf, bg = "white")
}
num <- function(x) format(round(x), big.mark = ",", trim = TRUE)
pct <- function(x) paste0(round(x), "%")

raw <- read.csv("../docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv",
                colClasses = "character")[, c("year", "study_design_final")]
N <- nrow(raw)
raw$year <- as.integer(raw$year)

# ---- numbers ---------------------------------------------------------------------
REVIEW <- "Reviews of studies"
n_review <- sum(raw$study_design_final == REVIEW, na.rm = TRUE)
n_empirical <- N - n_review
n_recent <- sum(raw$year >= 2019)
stopifnot(N == 53411, n_empirical == 49800, n_recent == 29190)

# Same text-only strip of headline numbers as the glance figures.
kpi_strip <- function(vals, labs) {
  d <- data.frame(x = (seq_along(vals) - 1) / length(vals), v = vals, l = labs)
  ggplot(d) +
    geom_text(aes(x, 1, label = v), hjust = 0, vjust = 1, fontface = "bold", size = 6.2, colour = hee_ink$primary) +
    geom_text(aes(x, 0.5, label = l), hjust = 0, vjust = 1, size = 2.5, colour = hee_ink$secondary,
              lineheight = 1.05) +
    scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) +
    scale_y_continuous(limits = c(-0.1, 1.02), expand = c(0, 0)) +
    theme_void() + theme(plot.margin = margin(6, 0, 0, 0))
}
k <- kpi_strip(
  c(num(N), pct(100 * n_empirical / N), pct(100 * n_recent / N)),
  c(paste0("health financing studies,\n", min(raw$year), "-", max(raw$year)),
    paste0("are empirical analyses\n(", num(n_empirical), " studies)"),
    paste0("published in 2019 or later\n(", num(n_recent), " studies)")))

# ---- A: study designs --------------------------------------------------------------
# One bar per design. The four designs the text names are full blue, other empirical
# designs a lighter blue, reviews orange (not empirical) and unclassified grey.
des <- as.data.frame(table(design = ifelse(is.na(raw$study_design_final) | raw$study_design_final == "",
                                           "Not classified", raw$study_design_final)),
                     stringsAsFactors = FALSE)
names(des)[2] <- "n"
des$share <- 100 * des$n / N
named4 <- head(des$design[order(-des$n)][des$design[order(-des$n)] != REVIEW], 4)
des$group <- ifelse(des$design %in% named4, "Most common empirical designs",
             ifelse(des$design == REVIEW, "Reviews of studies",
             ifelse(des$design == "Not classified", "Not classified", "Other empirical designs")))
des$group <- factor(des$group, c("Most common empirical designs", "Other empirical designs",
                                 "Reviews of studies", "Not classified"))
# unclassified last, everything else by size
des$design <- factor(des$design, des$design[order(des$design == "Not classified", -des$n, decreasing = TRUE)])
des$lab <- paste0(num(des$n), " (", pct(des$share), ")")
pal_A <- c("Most common empirical designs" = hee_cat[["blue"]], "Other empirical designs" = hee_seq[4],
           "Reviews of studies" = hee_cat[["orange"]], "Not classified" = hee_ink$muted)

pA <- ggplot(des, aes(n, design, fill = group)) +
  geom_col(width = 0.72) +
  geom_text(aes(label = lab), hjust = 0, nudge_x = 180, size = 2.4, colour = hee_ink$secondary) +
  scale_fill_manual(values = pal_A) +
  scale_x_continuous(labels = label_comma(), expand = expansion(mult = c(0, 0.2)), breaks = seq(0, 12000, 4000)) +
  guides(fill = guide_legend(nrow = 2)) +
  labs(title = "B  Study design", x = "Studies", y = NULL) +
  theme_hee(grid = "x") +
  theme(plot.title = element_text(size = rel(1.05)), legend.text = element_text(size = rel(0.8)),
        plot.margin = margin(8, 0, 4, 0))

# ---- B: studies per year -------------------------------------------------------------
# Bars, not a line, so the 2019-or-later block reads as a sum. 2026 is an incomplete
# year (the search ran mid-year): drawn hollow and labelled so it is not read as a fall.
yr <- as.data.frame(table(year = raw$year), stringsAsFactors = FALSE)
names(yr)[2] <- "n"
yr$year <- as.integer(yr$year)
yr$period <- ifelse(yr$year >= 2019, "2019 or later", "Before 2019")
yr$partial <- yr$year == PARTIAL_YEAR
pal_B <- c("Before 2019" = hee_seq[4], "2019 or later" = hee_cat[["blue"]])
ytop <- max(yr$n) * 1.28

pB <- ggplot(yr, aes(year, n)) +
  geom_col(data = yr[!yr$partial, ], aes(fill = period), width = 0.78) +
  geom_col(data = yr[yr$partial, ], fill = "white", colour = hee_cat[["blue"]], linewidth = 0.45, width = 0.78) +
  annotate("text", x = PARTIAL_YEAR, y = yr$n[yr$partial] + 120, label = "partial\nyear",
           vjust = 0, size = 2.2, lineheight = 0.95, colour = hee_ink$muted) +
  # bracket over the 2019-or-later bars
  annotate("segment", x = 2018.6, xend = max(yr$year) + 0.4, y = ytop * 0.9, yend = ytop * 0.9,
           linewidth = 0.35, colour = hee_ink$secondary) +
  annotate("segment", x = c(2018.6, max(yr$year) + 0.4), xend = c(2018.6, max(yr$year) + 0.4),
           y = ytop * 0.9, yend = ytop * 0.86, linewidth = 0.35, colour = hee_ink$secondary) +
  annotate("text", x = (2018.6 + max(yr$year) + 0.4) / 2, y = ytop * 0.93, vjust = 0, size = 2.5,
           label = paste0(num(n_recent), " studies (", pct(100 * n_recent / N), ")"),
           fontface = "bold", colour = hee_ink$primary) +
  annotate("text", x = (min(yr$year) + 2018.4) / 2, y = ytop * 0.93, vjust = 0, size = 2.5,
           label = paste0(num(N - n_recent), " studies (", pct(100 * (N - n_recent) / N), ")"),
           colour = hee_ink$secondary) +
  annotate("segment", x = min(yr$year) - 0.4, xend = 2018.4, y = ytop * 0.9, yend = ytop * 0.9,
           linewidth = 0.35, colour = hee_ink$muted) +
  scale_fill_manual(values = pal_B, guide = "none") +
  scale_x_continuous(breaks = seq(2010, 2026, 2), expand = expansion(add = 0.6)) +
  scale_y_continuous(labels = label_comma(), limits = c(0, ytop), expand = c(0, 0)) +
  labs(title = "A  Studies by year of publication", x = NULL, y = "Studies") +
  theme_hee(grid = "y") +
  theme(plot.title = element_text(size = rel(1.05)), legend.text = element_text(size = rel(0.8)),
        plot.margin = margin(8, 0, 4, 0))

# ---- assemble -----------------------------------------------------------------------
# Growth first (the section's headline), then the design breakdown, both full width.
fig <- wrap_elements(full = k) / wrap_elements(full = pB) / wrap_elements(full = pA) +
  plot_layout(heights = c(0.2, 0.75, 1)) +
  plot_annotation(
    title = "Research on health financing functions is large and growing fast",
    caption = paste0("n = ", num(N), " included studies. Panel A: ", PARTIAL_YEAR, " is an incomplete year because the search ran ",
                     "mid-year; it is included in the 2019-or-later total. Panel B: one study design per study; reviews of ",
                     "studies synthesise evidence on focused health financing topics, all other designs are ",
                     "empirical analyses."),
    theme = theme_hee() + theme(plot.margin = margin(12, 14, 10, 12)))

save_fig(fig, "fig_section321_size_and_growth", 8.2)

# make_glance_figures_v2.R — v2 of make_glance_figures.R (that script and its PNGs are kept).
#
# Changes from v1:
#   figure 1: no coverage note; panel A is the distribution of studies (studies per
#             100,000 DALYs, one blue ramp on a log scale, as in the HEE reference)
#             instead of the leading-function map;
#   figure 2: each region's coverage of all nine financing functions (bars, with the
#             function names in a shared label column) replaces the dot grid and the
#             top-three list.
#
#   fig_glance_1_evidence_at_a_glance_v2   headline numbers, A: studies per 100,000 DALYs
#   fig_glance_2_profile_by_region_v2      headline numbers, one column per WHO region
#
# Run prep_data.py first. Then, from this folder:
#   Rscript make_glance_figures_v2.R

.libPaths(c("_rlib", .libPaths()))
source("theme_hee.R")  # copy of docs/theme_hee.R
suppressPackageStartupMessages({ library(sf); library(rnaturalearth); library(patchwork) })

W_IN <- 7.2  # full journal page width (183 mm)
save_fig <- function(p, name, h) {
  ggsave(paste0(name, ".png"), p, width = W_IN, height = h, dpi = 300, device = ragg::agg_png, bg = "white")
  ggsave(paste0(name, ".pdf"), p, width = W_IN, height = h, device = cairo_pdf, bg = "white")
}
pct <- function(x) paste0(round(x), "%")
num <- function(x) format(round(x), big.mark = ",", trim = TRUE)
wrap <- function(x, w) vapply(x, function(s) paste(strwrap(s, w), collapse = "\n"), "")

kp <- read.csv("kpis.csv")
K <- setNames(kp$value, kp$key)
Kn <- function(k) as.numeric(K[[k]])

# Text-only strip of headline numbers, like the reference's top row.
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

FN_SHORT <- c("Revenue Raising" = "Revenue raising", "Overall" = "Financing system as a whole",
              "Recurrent financing for the procurement and distribution of supply chain inputs" =
                "Supply-chain financing",
              "Capital investment: other health system inputs" = "Capital investment: other inputs")
short_fn <- function(x) ifelse(x %in% names(FN_SHORT), FN_SHORT[x], x)

# ---- figure 1: the evidence at a glance ------------------------------------------
# Country count and study-country pairs as reported in the manuscript text (3.2.2), which
# come from a different country matching than the site data drawn here (184; 47,693).
MS_COUNTRIES <- 198
MS_PAIRS <- 47488
k1 <- kpi_strip(
  c(num(Kn("n_studies")), num(MS_COUNTRIES), pct(Kn("fp_pct_outcome")), pct(Kn("oa_pct")), pct(Kn("lmic_pct"))),
  c(paste0("studies, ", K[["year0"]], "-", K[["year1"]]), "countries or territories\nwith at least one study",
    "investigate financial\nprotection as an outcome", "open access",
    "focus on low- and middle-\nincome countries"))

# Studies per person-year of disease burden is a magnitude: one hue, light to dark.
# hee_ord keeps the lightest step distinct from the grey used for no rate.
rates <- read.csv("map_per100k_dalys.csv")
n_rated <- sum(!is.na(rates$per100k_dalys))
ne_to_iso <- c(SDS = "SSD", PSX = "PSE", KOS = "XKX", SOL = "SOM", CYN = "CYP")
world <- ne_countries(scale = 50, returnclass = "sf")
world <- world[world$adm0_a3 != "ATA", ]
world$iso3 <- ifelse(world$adm0_a3 %in% names(ne_to_iso), ne_to_iso[world$adm0_a3], world$adm0_a3)
world <- merge(world, rates[, c("iso3", "per100k_dalys")], by = "iso3", all.x = TRUE)
world <- st_transform(world, "+proj=robin")
breaks <- c(0.1, 0.3, 1, 3, 10, 30)

pA <- ggplot(world) +
  geom_sf(aes(fill = per100k_dalys), colour = "white", linewidth = 0.1) +
  scale_fill_gradientn(colours = hee_ord, trans = "log10", limits = range(breaks), breaks = breaks,
                       labels = c("0.1", "0.3", "1", "3", "10", "30"), oob = squish, na.value = hee_ink$grid,
                       name = "Studies per 100,000 DALYs (log scale)",
                       guide = guide_colourbar(barwidth = unit(170, "pt"), barheight = unit(6, "pt"),
                                               title.position = "top")) +
  coord_sf(expand = FALSE, datum = NA) +
  labs(title = paste0("Geographic distribution of health financing studies (n = ", num(MS_PAIRS),
                      " study-country pairs)")) +
  theme_hee(grid = "none") +
  theme(axis.text = element_blank(), axis.title = element_blank(), legend.location = "plot",
        legend.title = element_text(size = rel(0.85), colour = hee_ink$secondary, margin = margin(b = 2)),
        plot.title = element_text(face = "bold", size = rel(1.0), margin = margin(b = 4)),
        plot.margin = margin(8, 0, 0, 0))

fig1 <- k1 / wrap_elements(full = pA) +
  plot_layout(heights = c(0.8, 4.0)) +
  plot_annotation(
    title = "The evidence at a glance",
    caption = paste0(
      "HFF dataset v2.5.1, studies published ", K[["year0"]], "-", K[["year1"]], " (", K[["year1"]], " is incomplete). ",
      "Map: studies naming each country per 100,000 disability-adjusted life years (DALYs, GBD 2023), for the ",
      n_rated, " countries with at least one study and burden data; a study naming several countries counts in ",
      "each. Log scale; values below 0.1 or above 30 take the end colours. Grey: no study naming the country, no ",
      "burden data (Hong Kong, Kosovo) or outside the country data. Open access: share of studies with a DOI ",
      "(OpenAlex). Financial protection: share of the ", num(Kn("n_with_outcome")), " studies with an outcome domain ",
      "other than 'Unclear'. Low- and middle-income: share of studies naming a country that name at least one (World Bank ",
      "income groups)."),
    theme = theme_hee())
save_fig(fig1, "fig_glance_1_evidence_at_a_glance_v4", 5.7)

# ---- figure 2: profile of studies by WHO region ----------------------------------
REGIONS <- c(AFR = "African Region", AMR = "Region of the Americas", SEAR = "South-East Asia Region",
             EUR = "European Region", EMR = "Eastern Mediterranean Region", WPR = "Western Pacific Region")
rf <- read.csv("region_functions.csv")
rf$fn <- short_fn(rf$function.)
fn_order <- names(sort(tapply(rf$share * rf$n_fn_tagged, rf$fn, sum), decreasing = TRUE))
fp <- read.csv("region_fp.csv")
tr <- read.csv("region_trend.csv")
all_tr <- tr[tr$region == "All regions", ]
cov_all <- tail(all_tr$at_least_one, 1)

k2 <- kpi_strip(
  c(pct(Kn("top_fn_pct")), pct(Kn("fp_pct_outcome")), pct(cov_all)),
  c(paste0("of function-tagged studies address\n", tolower(short_fn(K[["top_fn"]])), ", the most studied"),
    "investigate financial protection\nas an outcome",
    paste0("of countries named by at least one\nstudy by ", max(tr$year))))

# Shared canvas for the label column and the region columns: x 0-1, y 0 (top) to 100.
FN_Y <- setNames(25 + (seq_along(fn_order) - 1) * 5.6, fn_order)  # one row per function
FN_MAX <- 30   # function bars run 0-30% of the region's function-tagged studies
FP_MAX <- 30   # financial protection bar runs 0-30% of the region's studies with a recorded outcome
BAR_W <- 0.7   # bar length at the scale maximum, leaving room for the % label
txt <- function(x, y, label, ...) annotate("text", x = x, y = y, label = label, vjust = 1, ...)
canvas <- function(p, right = 10) {
  p + scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) +
    scale_y_reverse(limits = c(100, -1), expand = c(0, 0)) +
    coord_cartesian(clip = "off") + theme_void() + theme(plot.margin = margin(0, right, 0, 0))
}

label_column <- canvas(ggplot() +
  txt(0, 15.5, "Financing functions", hjust = 0, fontface = "bold", size = 2.4, colour = hee_ink$primary) +
  txt(0, 19.3, "Share of function-tagged studies", hjust = 0, size = 2.0, colour = hee_ink$muted) +
  txt(0, FN_Y - 0.4, wrap(fn_order, 22), hjust = 0, size = 2.15, colour = hee_ink$secondary, lineheight = 0.9) +
  txt(0, 80, "Financial protection\nas an outcome", hjust = 0, fontface = "bold", size = 2.4,
      colour = hee_ink$primary, lineheight = 0.95) +
  txt(0, 89.5, "Share of studies with a recorded\noutcome; orange = all regions", hjust = 0, size = 2.0, colour = hee_ink$muted,
      lineheight = 0.95), right = 6)

region_column <- function(code) {
  r <- REGIONS[[code]]
  d <- rf[rf$region == r, ]
  d$y <- FN_Y[d$fn]
  d$top <- d$share == max(d$share)
  f <- fp[fp$region == r, ]
  canvas(ggplot() +
    txt(0, 0, code, hjust = 0, fontface = "bold", size = 3.6, colour = hee_ink$primary) +
    txt(0, 6.5, wrap(r, 17), hjust = 0, size = 2.3, colour = hee_ink$secondary, lineheight = 0.95) +
    txt(0, 16.5, paste0("n = ", num(d$n_studies[1])), hjust = 0, size = 2.3, colour = hee_ink$primary) +
    annotate("rect", xmin = 0, xmax = BAR_W, ymin = d$y - 0.2, ymax = d$y + 2.2, fill = hee_ink$grid) +
    annotate("rect", xmin = 0, xmax = pmin(d$share, FN_MAX) / FN_MAX * BAR_W, ymin = d$y - 0.2, ymax = d$y + 2.2,
             fill = ifelse(d$top, hee_seq[11], hee_cat[["blue"]])) +
    txt(1, d$y - 0.6, pct(d$share), hjust = 1, size = 2.15, colour = hee_ink$primary,
        fontface = ifelse(d$top, "bold", "plain")) +
    txt(0, 80, paste0(pct(f$fp_share_outcome), " investigate\nfinancial protection"), hjust = 0, fontface = "bold",
        size = 2.3, colour = hee_ink$primary, lineheight = 0.95) +
    annotate("rect", xmin = 0, xmax = 1, ymin = 90, ymax = 93, fill = hee_ink$grid) +
    annotate("rect", xmin = 0, xmax = f$fp_share_outcome / FP_MAX, ymin = 90, ymax = 93, fill = hee_cat[["blue"]]) +
    annotate("segment", x = f$all_outcome_fp_share / FP_MAX, xend = f$all_outcome_fp_share / FP_MAX,
             y = 89, yend = 94, colour = hee_cat[["orange"]], linewidth = 0.6))
}

trend_plot <- function(code, first) {
  d <- tr[tr$region == REGIONS[[code]], ]
  ggplot(d, aes(year)) +
    geom_line(data = all_tr, aes(y = at_least_one), colour = hee_ink$muted, linewidth = 0.45) +
    geom_line(aes(y = two_or_more), colour = hee_ink$primary, linewidth = 0.45, linetype = "22") +
    geom_line(aes(y = at_least_one), colour = hee_ink$primary, linewidth = 0.5) +
    scale_x_continuous(breaks = range(d$year)) +
    scale_y_continuous(limits = c(0, 100), breaks = c(0, 100), labels = c("0%", "100%")) +
    labs(x = NULL, y = NULL) +
    theme_hee(grid = "y", base_size = 7) +
    theme(axis.text.x = element_text(hjust = c(0, 1)), plot.margin = margin(2, 10, 2, 0),
          axis.text.y = if (first) element_text() else element_blank())
}
trend_label <- canvas(ggplot() +
  txt(0, 2, "Countries with a study,\nover time", hjust = 0, fontface = "bold", size = 2.4,
      colour = hee_ink$primary, lineheight = 0.95) +
  txt(0, 30, "Solid: at least 1\nDashed: 2 or more\nGrey: all regions,\nat least 1", hjust = 0, size = 2.0,
      colour = hee_ink$muted, lineheight = 1.0), right = 6)

widths <- c(1.35, rep(1, length(REGIONS)))
cols <- wrap_plots(c(list(label_column), lapply(names(REGIONS), region_column)), nrow = 1, widths = widths)
trends <- wrap_plots(c(list(trend_label), lapply(seq_along(REGIONS), function(i) trend_plot(names(REGIONS)[i], i == 1))),
                     nrow = 1, widths = widths)

fig2 <- k2 / cols / trends +
  plot_layout(heights = c(0.8, 4.0, 0.85)) +
  plot_annotation(
    title = "Profile of studies by WHO region",
    caption = paste0(
      "Studies naming countries in several regions count in each. Financing functions: share of the region's ",
      "function-tagged studies addressing each function, on a 0-", FN_MAX, "% scale (darker bar and bold = the ",
      "function studied most); a study can address several functions, so a region's shares sum to more than ",
      "100%. Financial protection: share of the region's studies with a recorded outcome (an outcome domain other ",
      "than 'Unclear'; ", num(Kn("n_with_outcome")), " studies in all) that examine financial protection, on a 0-", FP_MAX,
      "% scale; orange marker: all such studies (", pct(Kn("fp_pct_outcome")), "). Trends: cumulative share ",
      "of the region's countries with at least one study (solid) or two or more (dashed); grey: all regions, at ",
      "least one; ", max(tr$year) + 1, " is left out as incomplete. 'Other' and 'Unclear' function tags are left ",
      "out throughout."),
    theme = theme_hee())
save_fig(fig2, "fig_glance_2_profile_by_region_v3", 6.6)

cat("done\n")

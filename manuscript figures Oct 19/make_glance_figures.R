# make_glance_figures.R — the "evidence at a glance" pair, laid out like the HEE
# reference figures, in theme_hee style.
#
#   fig_glance_1_evidence_at_a_glance   headline numbers, country coverage note, A: map
#   fig_glance_2_profile_by_region      headline numbers, one column per WHO region
#
# Run prep_data.py first. Then, from this folder:
#   Rscript make_glance_figures.R

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

# Function grouping shared by the map, the dot grids and their legend. A choropleth
# may use only the three all-pairs-safe slots, so the three functions leading the
# most countries are coloured and the rest fold into one neutral.
lf <- read.csv("leading_function.csv")
lead_n <- sort(table(lf$leading_function[lf$status == "lead"]), decreasing = TRUE)
top3 <- names(lead_n)[1:3]
FN_SHORT <- c("Revenue Raising" = "Revenue raising", "Overall" = "Financing system as a whole",
              "Recurrent financing for the procurement and distribution of supply chain inputs" =
                "Supply-chain financing",
              "Capital investment: other health system inputs" = "Capital investment: other inputs")
short_fn <- function(x) ifelse(x %in% names(FN_SHORT), FN_SHORT[x], x)
grp_lev <- c(short_fn(top3), "Another function")
pal_grp <- setNames(c(hee_cat3, hee_ink$muted), grp_lev)
others <- tolower(short_fn(setdiff(names(lead_n), top3)))
others_txt <- paste0(paste(others[-length(others)], collapse = ", "), " or ", others[length(others)])

# ---- figure 1: the evidence at a glance ------------------------------------------
k1 <- kpi_strip(
  c(num(Kn("n_studies")), num(Kn("n_countries_named")), pct(Kn("fp_pct")), pct(Kn("oa_pct")), pct(Kn("lmic_pct"))),
  c(paste0("studies, ", K[["year0"]], "-", K[["year1"]]), "countries or territories\nwith at least one study",
    "investigate financial\nprotection as an outcome", "open access",
    "focus on low- and middle-\nincome countries"))

n_lead <- sum(lf$status == "lead"); n_tie <- sum(lf$status == "tie"); n_few <- sum(lf$status == "few")
note_txt <- paste0(
  "The evidence base covers ", num(Kn("n_countries_named")), " of the ", num(Kn("n_countries_data")),
  " countries and territories in the country data: ", num(Kn("n_country_named_studies")), " of the ",
  num(Kn("n_studies")), " studies name at least one country, giving ", num(Kn("n_pairs")),
  " study-country pairs (a study naming several countries counts in each). In the map, ", n_lead,
  " countries have a clear leading financing function, ", n_tie, " have a tie and ", n_few,
  " have fewer than 5 function-tagged studies.")
note <- ggplot() +
  ggtext::geom_textbox(aes(x = 0, y = 1, label = note_txt), hjust = 0, vjust = 1, halign = 0, box.colour = NA,
                       fill = NA, width = unit(1, "npc"), size = 2.5, colour = hee_ink$secondary,
                       box.padding = unit(c(0, 0, 0, 0), "pt"), lineheight = 1.25) +
  scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) + scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
  theme_void()

ne_to_iso <- c(SDS = "SSD", PSX = "PSE", KOS = "XKX", SOL = "SOM", CYN = "CYP")
world <- ne_countries(scale = 50, returnclass = "sf")
world <- world[world$adm0_a3 != "ATA", ]
world$iso3 <- ifelse(world$adm0_a3 %in% names(ne_to_iso), ne_to_iso[world$adm0_a3], world$adm0_a3)
lf$cls <- ifelse(lf$status == "lead" & lf$leading_function %in% top3, short_fn(lf$leading_function),
          ifelse(lf$status == "lead", "Another function", "Tie, or under 5 studies"))
map_lev <- c(grp_lev, "Tie, or under 5 studies")
world <- merge(world, lf[, c("iso3", "cls")], by = "iso3", all.x = TRUE)
world$cls <- factor(world$cls, levels = map_lev)
world <- st_transform(world, "+proj=robin")
n_cls <- table(factor(lf$cls[lf$status != "none"], levels = map_lev))

pA <- ggplot(world) +
  geom_sf(aes(fill = cls), colour = "white", linewidth = 0.1) +
  scale_fill_manual(values = c(pal_grp, "Tie, or under 5 studies" = hee_ink$grid), breaks = map_lev,
                    labels = paste0(map_lev, " (", n_cls, ")"), na.value = "#f6f5f2", drop = FALSE) +
  coord_sf(expand = FALSE, datum = NA) +
  labs(title = paste0("A  Financing function studied most often, by country (n = ", num(Kn("n_pairs")),
                      " study-country pairs)")) +
  theme_hee(grid = "none") +
  theme(axis.text = element_blank(), axis.title = element_blank(), legend.location = "plot",
        plot.title = element_text(face = "bold", size = rel(1.0), margin = margin(b = 4)),
        plot.margin = margin(8, 0, 0, 0)) +
  guides(fill = guide_legend(nrow = 2, byrow = TRUE))

fig1 <- k1 / note / wrap_elements(full = pA) +
  plot_layout(heights = c(0.8, 0.42, 4.0)) +
  plot_annotation(
    title = "The evidence at a glance",
    caption = paste0(
      "HFF dataset v2.5.1, studies published ", K[["year0"]], "-", K[["year1"]], " (", K[["year1"]], " is incomplete). ",
      "Map: each country takes the financing function tagged most often among the studies naming it; numbers in ",
      "brackets are countries. A study can address several functions; 'Other' and 'Unclear' tags are left out. ",
      "'Another function': ", others_txt, ". 'Under 5 studies': fewer than 5 function-tagged studies. Palest grey: ",
      "no study naming the country, or outside the country data. Open access: share of studies with a DOI ",
      "(OpenAlex). Low- and middle-income: share of studies naming a country that name at least one (World Bank ",
      "income groups)."),
    theme = theme_hee())
save_fig(fig1, "fig_glance_1_evidence_at_a_glance", 6.0)

# ---- figure 2: profile of studies by WHO region ----------------------------------
REGIONS <- c(AFR = "African Region", AMR = "Region of the Americas", SEAR = "South-East Asia Region",
             EUR = "European Region", EMR = "Eastern Mediterranean Region", WPR = "Western Pacific Region")
rf <- read.csv("region_functions.csv")
rf$fn <- short_fn(rf$function.)
rf$tags <- rf$share / 100 * rf$n_fn_tagged
rf$grp <- ifelse(rf$fn %in% grp_lev, rf$fn, "Another function")
fp <- read.csv("region_fp.csv")
tr <- read.csv("region_trend.csv")
all_tr <- tr[tr$region == "All regions", ]
cov_all <- tail(all_tr$at_least_one, 1)

k2 <- kpi_strip(
  c(pct(Kn("top_fn_pct")), pct(Kn("fp_pct")), pct(cov_all)),
  c(paste0("of function-tagged studies address \n", tolower(short_fn(K[["top_fn"]])), ", the most studied"),
    "investigate financial protection\nas an outcome",
    paste0("of countries named by at least one\nstudy by ", max(tr$year))))

legend_strip <- ggplot(data.frame(g = factor(grp_lev, levels = grp_lev), x = 1, y = 1)) +
  geom_point(aes(x, y, colour = g), size = 0, alpha = 0) +
  scale_colour_manual(values = pal_grp) +
  guides(colour = guide_legend(nrow = 1, override.aes = list(size = 2.6, alpha = 1, shape = 16))) +
  theme_void() +
  theme(legend.position = "top", legend.justification = "left", legend.location = "plot",
        legend.title = element_blank(), legend.text = element_text(size = 7, colour = hee_ink$secondary),
        legend.margin = margin(0, 0, 0, 0))

largest_remainder <- function(v, total = 100) {
  q <- v / sum(v) * total
  out <- floor(q)
  extra <- order(q - out, decreasing = TRUE)[seq_len(total - sum(out))]
  out[extra] <- out[extra] + 1
  out
}

# One column per region on an abstract canvas: x 0-1, y 0 (top) to 100 (bottom).
FP_MAX <- 25
region_column <- function(code) {
  r <- REGIONS[[code]]
  d <- rf[rf$region == r, ]
  g <- tapply(d$tags, factor(d$grp, levels = grp_lev), sum)
  dots <- largest_remainder(g)
  waffle <- data.frame(i = 0:99, grp = factor(rep(grp_lev, dots), levels = grp_lev))
  waffle$x <- 0.05 + (waffle$i %% 10) * 0.1
  waffle$y <- 27 + (waffle$i %/% 10) * 2.7
  top <- head(d[order(-d$share), ], 3)
  top$y <- c(66, 73, 80)
  f <- fp[fp$region == r, ]
  txt <- function(x, y, label, ...) annotate("text", x = x, y = y, label = label, vjust = 1, ...)
  ggplot() +
    txt(0, 0, code, hjust = 0, fontface = "bold", size = 3.6, colour = hee_ink$primary) +
    txt(0, 6.5, wrap(r, 17), hjust = 0, size = 2.3, colour = hee_ink$secondary, lineheight = 0.95) +
    txt(0, 15.5, paste0("n = ", num(d$n_studies[1])), hjust = 0, size = 2.3, colour = hee_ink$primary) +
    txt(0, 20.5, paste0(num(d$n_fn_tagged[1]), " function-tagged"), hjust = 0, size = 2.0, colour = hee_ink$muted) +
    geom_point(data = waffle, aes(x, y, colour = grp), size = 0.85) +
    txt(c(0.02, 0.36, 0.66, 1), 54.5, pct(100 * g / sum(g)), hjust = c(0, 0.5, 0.5, 1), size = 2.1,
        colour = pal_grp, fontface = "bold") +
    txt(0, 60, "Top three functions", hjust = 0, fontface = "bold", size = 2.3, colour = hee_ink$primary) +
    txt(0, top$y, wrap(top$fn, 18), hjust = 0, size = 2.15, colour = hee_ink$secondary, lineheight = 0.95) +
    txt(1, top$y, pct(top$share), hjust = 1, size = 2.15, colour = hee_ink$primary) +
    txt(0, 87, paste0(pct(f$fp_share), " investigate\nfinancial protection"), hjust = 0, fontface = "bold",
        size = 2.3, colour = hee_ink$primary, lineheight = 0.95) +
    annotate("rect", xmin = 0, xmax = 1, ymin = 95, ymax = 98, fill = hee_ink$grid) +
    annotate("rect", xmin = 0, xmax = f$fp_share / FP_MAX, ymin = 95, ymax = 98, fill = hee_cat[["blue"]]) +
    annotate("segment", x = f$all_studies_fp_share / FP_MAX, xend = f$all_studies_fp_share / FP_MAX,
             y = 94, yend = 99, colour = hee_cat[["orange"]], linewidth = 0.6) +
    scale_colour_manual(values = pal_grp, guide = "none") +
    scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) +
    scale_y_reverse(limits = c(100, -1), expand = c(0, 0)) +
    coord_cartesian(clip = "off") +
    theme_void() + theme(plot.margin = margin(0, 10, 0, 0))
}

trend_plot <- function(code, first) {
  r <- REGIONS[[code]]
  d <- tr[tr$region == r, ]
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

cols <- wrap_plots(lapply(names(REGIONS), region_column), nrow = 1)
trends <- wrap_plots(lapply(seq_along(REGIONS), function(i) trend_plot(names(REGIONS)[i], i == 1)), nrow = 1)

fig2 <- k2 / legend_strip / cols / trends +
  plot_layout(heights = c(0.8, 0.18, 4.2, 0.85)) +
  plot_annotation(
    title = "Profile of studies by WHO region",
    caption = paste0(
      "Studies naming countries in several regions count in each. Dots: share of the region's function tags in ",
      "each group, one dot = 1% ('Another function' = ", others_txt, "); a study can address several functions. ",
      "Top three: share of the region's function-tagged studies addressing each function. Financial protection ",
      "bar: share of the region's studies with financial protection among their outcomes, on a 0-", FP_MAX,
      "% scale; orange marker: all studies (", pct(Kn("fp_pct")), "). Trends: cumulative share of the region's ",
      "countries with at least one study (solid) or two or more (dashed); grey: all regions, at least one; ",
      max(tr$year) + 1, " is left out as incomplete. 'Other' and 'Unclear' function tags are left out throughout."),
    theme = theme_hee())
save_fig(fig2, "fig_glance_2_profile_by_region", 6.9)

cat("done\n")

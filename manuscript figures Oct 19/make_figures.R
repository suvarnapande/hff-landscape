# make_figures.R — redraws manuscript figures 1 and 8 in theme_hee style.
#
#   fig1_studies_per_10m_map     studies per 10 million people, by country studied
#   fig8_aid_vs_research_region  share of health aid vs share of research, by region
#
# Run prep_data.py first (writes the two CSVs). Then, from this folder:
#   Rscript make_figures.R
# ggtext is loaded from ./_rlib (installed there so the user's R library is untouched).

.libPaths(c("_rlib", .libPaths()))
source("theme_hee.R")  # copy of docs/theme_hee.R
suppressPackageStartupMessages({ library(sf); library(rnaturalearth) })

W_IN <- 7.2  # full journal page width (183 mm)
save_fig <- function(p, name, h) {
  ggsave(paste0(name, ".png"), p, width = W_IN, height = h, dpi = 300, device = ragg::agg_png, bg = "white")
  ggsave(paste0(name, ".pdf"), p, width = W_IN, height = h, device = cairo_pdf, bg = "white")
}

# ---- fig 1: map ----------------------------------------------------------------
# Studies per person is a magnitude, so the theme's one-hue ramp, not a red/blue
# diverging scale. hee_ord (not the full hee_seq) keeps the lightest step >= 2:1 on
# paper, so it stays distinct from the grey used for no data.
rates <- read.csv("map_per10m.csv")
# Natural Earth codes that differ from the site's ISO3, plus breakaway areas drawn
# with the country they are counted under.
ne_to_iso <- c(SDS = "SSD", PSX = "PSE", KOS = "XKX", SOL = "SOM", CYN = "CYP")
world <- ne_countries(scale = 50, returnclass = "sf")
world <- world[world$adm0_a3 != "ATA", ]
world$iso3 <- ifelse(world$adm0_a3 %in% names(ne_to_iso), ne_to_iso[world$adm0_a3], world$adm0_a3)
world <- merge(world, rates[, c("iso3", "per10m")], by = "iso3", all.x = TRUE)
world <- st_transform(world, "+proj=robin")

n_pairs <- sum(rates$studies)
n_rated <- sum(!is.na(rates$per10m))
breaks <- c(3, 10, 30, 100, 300, 1000)

p1 <- ggplot(world) +
  geom_sf(aes(fill = per10m), colour = "white", linewidth = 0.1) +
  scale_fill_gradientn(colours = hee_ord, trans = "log10", limits = range(breaks),
                       breaks = breaks, labels = label_comma(), oob = squish,
                       na.value = hee_ink$grid,
                       guide = guide_colourbar(barwidth = unit(150, "pt"), barheight = unit(6, "pt"))) +
  coord_sf(expand = FALSE, datum = NA) +
  labs(title = "Health financing studies per 10 million people, by country studied",
       caption = paste0(
         "Each study counts once in each country it names (", format(n_pairs, big.mark = ","), " study-country pairs across ",
         n_rated, " countries and territories). Population: World Bank. Log scale, darker = more studies per ",
         "person; values below 3 or above 1,000 take the end colours. Grey: no study naming the country, or no ",
         "population data.")) +
  theme_hee(grid = "none") +
  theme(axis.text = element_blank(), axis.title = element_blank())
save_fig(p1, "fig1_studies_per_10m_map", 4.3)

# ---- fig 8: aid vs research, by region -----------------------------------------
av <- read.csv("aid_vs_research.csv")
lev <- av$region  # already ordered by aid share, largest first
long <- rbind(
  data.frame(region = av$region, series = "Share of study-country pairs", share = av$research_share),
  data.frame(region = av$region, series = "Share of development assistance for health (2022-24 average)",
             share = av$aid_share))
long$region <- factor(long$region, levels = rev(lev))
long$series <- factor(long$series, levels = unique(long$series))
pal_av <- setNames(c(hee_cat[["blue"]], hee_cat[["orange"]]), levels(long$series))
ssa <- av[av$region == "Sub-Saharan Africa", ]

p8 <- ggplot(long, aes(x = share, y = region, fill = series)) +
  geom_col(position = position_dodge(width = 0.78, reverse = TRUE), width = 0.72) +
  geom_text(aes(label = paste0(round(share), "%")), position = position_dodge(width = 0.78, reverse = TRUE),
            hjust = -0.2, size = 2.6, colour = hee_ink$secondary) +
  scale_fill_manual(values = pal_av) +
  scale_x_continuous(labels = function(x) paste0(x, "%"), expand = expansion(mult = c(0, 0.08)),
                     limits = c(0, 70)) +
  scale_y_discrete(labels = function(x) gsub(", and ", ",\nand ", x)) +
  labs(title = "How regional shares of health aid and research compare", x = "Share of the global total", y = NULL,
       caption = paste0(
         "Sub-Saharan Africa receives ", round(ssa$aid_share), "% of development assistance for health but ",
         "accounts for ", round(ssa$research_share), "% of study-country pairs; the two are different measures ",
         "and need not match. Regions are IHME's GBD super-regions, approximated by World Bank income group and ",
         "then UN M49 sub-region (not WHO regions). Aid: IHME Financing Global Health, 2022-24 average. ",
         "Research: ", format(sum(av$research_pairs), big.mark = ","), " study-country pairs; each study counts ",
         "once in each country it names.")) +
  theme_hee(grid = "x") +
  theme(legend.location = "plot") +
  guides(fill = guide_legend(nrow = 1))
save_fig(p8, "fig8_aid_vs_research_region", 4.4)

# ---- (Un)equal weight: financing function studied most often, by country -------
# Static version of the site's interactive page (fig_glance_functions.html). Seven
# functions lead somewhere, but a choropleth may use only the three all-pairs-safe
# slots (hee_cat3), so the three functions leading the most countries get a colour and
# the rest fold into one neutral; ties and thin evidence take the paper-grey.
lf <- read.csv("leading_function.csv")
top3 <- names(sort(table(lf$leading_function[lf$status == "lead"]), decreasing = TRUE))[1:3]
fn_label <- function(x) ifelse(x == "Revenue Raising", "Revenue raising", x)
cls <- ifelse(lf$status == "lead" & lf$leading_function %in% top3, fn_label(lf$leading_function),
       ifelse(lf$status == "lead", "Another function", "Tie, or under 5 studies"))
lf$cls <- cls
lev_lf <- c(fn_label(top3), "Another function", "Tie, or under 5 studies")
n_lev <- table(factor(lf$cls[lf$status != "none"], levels = lev_lf))
pal_lf <- setNames(c(hee_cat3, hee_ink$muted, hee_ink$grid), lev_lf)

world_lf <- ne_countries(scale = 50, returnclass = "sf")
world_lf <- world_lf[world_lf$adm0_a3 != "ATA", ]
world_lf$iso3 <- ifelse(world_lf$adm0_a3 %in% names(ne_to_iso), ne_to_iso[world_lf$adm0_a3], world_lf$adm0_a3)
world_lf <- merge(world_lf, lf[, c("iso3", "cls")], by = "iso3", all.x = TRUE)
world_lf$cls <- factor(world_lf$cls, levels = lev_lf)
world_lf <- st_transform(world_lf, "+proj=robin")
others <- setdiff(names(sort(table(lf$leading_function[lf$status == "lead"]), decreasing = TRUE)), top3)
others <- sub("Recurrent financing for the procurement and distribution of supply chain inputs",
              "supply-chain financing", others)
others <- sub("Overall", "the financing system as a whole", others)

p_uw <- ggplot(world_lf) +
  geom_sf(aes(fill = cls), colour = "white", linewidth = 0.1) +
  scale_fill_manual(values = pal_lf, breaks = lev_lf, labels = paste0(lev_lf, " (", n_lev, ")"),
                    na.value = "#f6f5f2", drop = FALSE) +
  coord_sf(expand = FALSE, datum = NA) +
  labs(title = "Financing function studied most often, by country studied",
       caption = paste0(
         "Each country takes the financing function tagged most often among the studies naming it ",
         "(numbers in brackets are countries). A study can address several functions; 'Other' and 'Unclear' ",
         "tags are left out. 'Under 5 studies': fewer than 5 function-tagged studies. 'Another function': ", paste(tolower(others[-length(others)]), collapse = ", "),
         " or ", tolower(others[length(others)]), ". Palest grey: no study naming the country, or outside the ",
         "country data. ", format(sum(lf$studies), big.mark = ","), " study-country pairs, HFF dataset v2.5.1.")) +
  theme_hee(grid = "none") +
  theme(axis.text = element_blank(), axis.title = element_blank(), legend.location = "plot") +
  guides(fill = guide_legend(nrow = 2, byrow = TRUE))
save_fig(p_uw, "fig_unequal_weight_leading_function_map", 4.5)

# ---- (Un)equal weight, full figure: map plus the region profiles -----------------
# Static counterpart of the whole web page: A the map above, B function mix by WHO
# region, C financial protection as an outcome, D country coverage over time.
library(patchwork)
REG_SHORT <- c("African Region" = "African", "Region of the Americas" = "Americas",
               "South-East Asia Region" = "South-East Asia", "European Region" = "European",
               "Eastern Mediterranean Region" = "Eastern Mediterranean",
               "Western Pacific Region" = "Western Pacific")
FN_SHORT <- c("Revenue Raising" = "Revenue raising", "Overall" = "Financing system as a whole",
              "Recurrent financing for the procurement and distribution of supply chain inputs" =
                "Supply-chain financing",
              "Capital investment: other health system inputs" = "Capital investment: other inputs")
short_fn <- function(x) ifelse(x %in% names(FN_SHORT), FN_SHORT[x], x)
panel_title <- theme(plot.title = element_text(face = "bold", size = rel(1.0), colour = hee_ink$primary,
                                               margin = margin(b = 4)))

rf <- read.csv("region_functions.csv")
rf$fn <- short_fn(rf$function.)
fn_order <- names(sort(tapply(rf$share * rf$n_fn_tagged, rf$fn, sum)))  # least to most, bottom to top
rf$fn <- factor(rf$fn, levels = fn_order)
reg_lab <- unique(rf[, c("region", "n_studies")])
wrap_reg <- c(African = "African", Americas = "Americas", "South-East Asia" = "South-East\nAsia",
              European = "European", "Eastern Mediterranean" = "Eastern\nMediterranean",
              "Western Pacific" = "Western\nPacific")
reg_lab$lab <- paste0(wrap_reg[REG_SHORT[reg_lab$region]], "\n(n = ",
                      format(reg_lab$n_studies, big.mark = ",", trim = TRUE), ")")
rf$col <- factor(reg_lab$lab[match(rf$region, reg_lab$region)], levels = reg_lab$lab)
rf$lead <- ave(rf$share, rf$region, FUN = function(v) v == max(v))

pB <- ggplot(rf, aes(col, fn, fill = share)) +
  geom_tile(colour = "white", linewidth = 0.6) +
  geom_text(aes(label = paste0(round(share), "%"), colour = share > 17,
                fontface = ifelse(lead == 1, "bold", "plain")), size = 2.5) +
  scale_fill_gradientn(colours = hee_seq, limits = c(0, 30), oob = squish, guide = "none") +
  scale_colour_manual(values = c(`TRUE` = "white", `FALSE` = hee_ink$primary), guide = "none") +
  scale_x_discrete(position = "top") +
  labs(title = "B  Financing functions studied, by WHO region", x = NULL, y = NULL) +
  theme_hee(grid = "none") + panel_title +
  theme(axis.text.x.top = element_text(lineheight = 1.1))

fp <- read.csv("region_fp.csv")
fp$reg <- factor(REG_SHORT[fp$region], levels = rev(REG_SHORT))
avg_fp <- fp$all_studies_fp_share[1]
N_STUDIES <- fp$all_studies_n[1]
pC <- ggplot(fp, aes(fp_share, reg)) +
  geom_col(fill = hee_cat[["blue"]], width = 0.65) +
  geom_vline(xintercept = avg_fp, colour = hee_ink$primary, linewidth = 0.4, linetype = "22") +
  # white-backed labels so a value sitting on the average line stays legible
  geom_label(aes(label = paste0(round(fp_share), "%")), hjust = -0.15, size = 2.5, colour = hee_ink$secondary,
             fill = "white", label.size = 0, label.padding = unit(1, "pt")) +
  annotate("text", x = avg_fp, y = 6.65, label = paste0("All studies ", round(avg_fp), "%"),
           hjust = -0.05, size = 2.4, colour = hee_ink$primary) +
  scale_x_continuous(labels = function(x) paste0(x, "%"), limits = c(0, 25), expand = expansion(mult = c(0, 0))) +
  scale_y_discrete(expand = expansion(add = c(0.6, 1))) +
  labs(title = "C  Financial protection as an outcome", x = "Share of the region's studies", y = NULL) +
  theme_hee(grid = "x") + panel_title

tr <- read.csv("region_trend.csv")
reg_tr <- tr[tr$region != "All regions", ]
all_tr <- tr[tr$region == "All regions", c("year", "at_least_one")]
long_tr <- rbind(
  data.frame(region = reg_tr$region, year = reg_tr$year, v = reg_tr$at_least_one, s = "At least 1 study"),
  data.frame(region = reg_tr$region, year = reg_tr$year, v = reg_tr$two_or_more, s = "2 or more studies"),
  do.call(rbind, lapply(unique(reg_tr$region), function(r)
    data.frame(region = r, year = all_tr$year, v = all_tr$at_least_one, s = "All regions, at least 1"))))
long_tr$s <- factor(long_tr$s, levels = c("At least 1 study", "2 or more studies", "All regions, at least 1"))
long_tr$reg <- factor(sub("Eastern Mediterranean", "Eastern Med.", REG_SHORT[long_tr$region]),
                      levels = sub("Eastern Mediterranean", "Eastern Med.", REG_SHORT))
pD <- ggplot(long_tr, aes(year, v, colour = s, linetype = s)) +
  geom_line(linewidth = 0.5) +
  facet_wrap(~reg, ncol = 3) +
  scale_colour_manual(values = c(hee_ink$primary, hee_ink$primary, hee_ink$muted)) +
  scale_linetype_manual(values = c("solid", "22", "solid")) +
  scale_x_continuous(breaks = c(2010, 2025)) +
  scale_y_continuous(limits = c(0, 100), breaks = c(0, 100), labels = function(x) paste0(x, "%")) +
  labs(title = "D  Countries with a study, over time", x = NULL, y = NULL) +
  guides(colour = guide_legend(nrow = 2), linetype = guide_legend(nrow = 2)) +
  theme_hee(grid = "y") + panel_title +
  # year labels pushed inward so neighbouring facets' 2025 and 2010 do not collide
  theme(legend.key.width = unit(14, "pt"), panel.spacing.x = unit(10, "pt"),
        axis.text.x = element_text(hjust = c(0, 1)), strip.clip = "off",
        strip.text = element_text(size = rel(0.85), face = "plain", colour = hee_ink$secondary))

pA <- p_uw + labs(title = "A  Financing function studied most often, by country", caption = NULL) + panel_title

# wrap_elements keeps the map from being aligned to (and squeezed by) B's row labels
full <- wrap_elements(full = pA) / pB / (wrap_elements(full = pC) + wrap_elements(full = pD) +
                                          plot_layout(widths = c(1, 1.6))) +
  plot_layout(heights = c(4.6, 2.7, 3.1)) +
  plot_annotation(
    title = "(Un)equal weight: which health financing functions research focuses on",
    caption = paste0(
      "HFF dataset v2.5.1: ", format(N_STUDIES, big.mark = ","), " studies, ", format(sum(lf$studies), big.mark = ","),
      " study-country pairs. A: each country takes the financing function tagged most often among the studies naming ",
      "it (numbers in brackets are countries; 'Under 5 studies' = fewer than 5 function-tagged studies; 'Another ",
      "function' = ", paste(tolower(others[-length(others)]), collapse = ", "), " or ", tolower(others[length(others)]),
      "). B: share of each region's function-tagged studies that address each function, bold = the function studied ",
      "most; a study can address several functions, so columns sum to more than 100%. C: share of the region's ",
      "studies with financial protection among their outcome domains. D: cumulative share of the region's countries ",
      "named by at least one, or two or more, studies, ", min(tr$year), "-", max(tr$year), " (2026, a partial year, ",
      "is left out). Regions: WHO; studies naming countries in several regions count in each. 'Other' and 'Unclear' ",
      "function tags are left out throughout."),
    theme = theme_hee())
save_fig(full, "fig_unequal_weight_full", 10.6)

cat("done\n")

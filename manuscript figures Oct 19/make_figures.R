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

cat("done\n")

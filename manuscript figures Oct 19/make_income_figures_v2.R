# make_income_figures_v2.R — manuscript figures 2 and 7 redrawn (22 October 2026) with income
# groups taken in the study's publication year. The earlier versions in "figs 2-7 screenshots/"
# are screen captures of figures that used the CURRENT (FY2027) World Bank group; they are kept.
#
#   fig2_functions_by_income_v2         share of single-country studies addressing each financing
#                                       function, high-income vs low- and middle-income countries
#   fig7_author_location_by_income_v2   where the authors of single-country studies are based,
#                                       by income group of the country studied
#
# Income group: the World Bank group of the country studied in the study's publication year
# (docs/data/geo.json "i"), as in prep_data_v2.py. Run prep_data_v2.py first. Then, from this folder:
#   Rscript make_income_figures_v2.R

.libPaths(c("_rlib", .libPaths()))
source("theme_hee.R")  # copy of docs/theme_hee.R

W_IN <- 7.2  # full journal page width (183 mm)
save_fig <- function(p, name, h) {
  ggsave(paste0(name, ".png"), p, width = W_IN, height = h, dpi = 300, device = ragg::agg_png, bg = "white")
  ggsave(paste0(name, ".pdf"), p, width = W_IN, height = h, device = cairo_pdf, bg = "white")
}
num <- function(x) format(round(x), big.mark = ",", trim = TRUE)
pct <- function(x) paste0(round(x), "%")
INCOME_NOTE <- "Income: World Bank income group of the country studied in the study's publication year."

# ---- figure 2: financing functions by income group -----------------------------------
f2 <- read.csv("fig2_functions_by_income_v2.csv")
f2$function. <- factor(f2$function., levels = rev(unique(f2$function.)))
f2$group <- factor(f2$group, levels = c("Low and middle income", "High income"),
                   labels = c("Low- and middle-income countries", "High-income countries"))
n2 <- tapply(f2$n, f2$group, `[`, 1)
p2 <- ggplot(f2, aes(share, function., fill = group)) +
  geom_col(position = position_dodge(width = 0.78), width = 0.72) +
  geom_text(aes(label = pct(share)), position = position_dodge(width = 0.78), hjust = -0.2, size = 2.5,
            colour = hee_ink$secondary) +
  scale_fill_manual(values = c("High-income countries" = hee_cat[["blue"]],
                               "Low- and middle-income countries" = hee_cat[["orange"]]),
                    breaks = c("High-income countries", "Low- and middle-income countries")) +
  scale_x_continuous(labels = function(x) paste0(x, "%"), expand = expansion(mult = c(0, 0.08))) +
  labs(title = "Financing functions studied, by income group of the country studied",
       x = "Share of single-country studies", y = NULL,
       caption = paste0("Base: single-country studies with a World Bank income group: ",
                        num(n2[["High-income countries"]]), " on high-income and ",
                        num(n2[["Low- and middle-income countries"]]), " on low- and middle-income countries. ",
                        INCOME_NOTE, " A study can address several functions.")) +
  theme_hee(grid = "x") +
  theme(legend.location = "plot")
save_fig(p2, "fig2_functions_by_income_v2", 4.2)

# ---- figure 7: author location by income group ---------------------------------------
f7 <- read.csv("fig7_author_location_by_income_v2.csv")
LOC <- c("Authors based only in the country studied", "Authors based in and outside the country",
         "No author based in the country")
f7$location <- factor(f7$location, levels = rev(LOC))
f7$income <- factor(f7$income, levels = rev(c("Low income", "Lower middle income", "Upper middle income",
                                              "High income")))
p7 <- ggplot(f7, aes(share, income, fill = location)) +
  geom_col(width = 0.7) +
  geom_text(aes(label = ifelse(share >= 5, pct(share), "")), position = position_stack(vjust = 0.5),
            size = 2.6, colour = "white") +
  scale_fill_manual(values = setNames(c(hee_cat[["blue"]], hee_ink$muted, hee_cat[["orange"]]), LOC),
                    breaks = LOC) +
  scale_x_continuous(labels = function(x) paste0(x, "%"), expand = c(0, 0)) +
  labs(title = "Where the authors of studies about each income group are based",
       x = "Share of single-country studies", y = NULL,
       caption = paste0(num(sum(f7$studies)), " single-country studies with at least one author affiliation ",
                        "country (OpenAlex). ", INCOME_NOTE, " Author locations do not show who led the research.")) +
  theme_hee(grid = "none") +
  theme(legend.location = "plot")
save_fig(p7, "fig7_author_location_by_income_v2", 3.2)

cat("done\n")

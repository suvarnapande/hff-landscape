# make_open_access_figure_v2.R — v2 of make_open_access_figure.R (22 October 2026; v1 and its
# output are kept). v1 grouped studies by the income_level column, which is the CURRENT (FY2027)
# World Bank group. v2 uses the World Bank income group of each country studied in the study's
# publication year (oa_by_income_v2.csv, from prep_data_v2.py, built from docs/data/geo.json "i"):
#   high income            = every country studied was high income in the publication year
#   low and middle income  = every country studied was low or middle income
#   both                   = countries from both groups
#   no income group        = no country named, or none with a group
# The manuscript's sentence ("... 73% of those on low- and middle-income countries and 59% of
# those on high-income countries") should quote the shares this script prints.
#
#   fig_open_access_by_income_v2   share open access, all studies with a DOI and by income group
#
# Run prep_data_v2.py first. Then, from this folder:
#   Rscript make_open_access_figure_v2.R

.libPaths(c("_rlib", .libPaths()))
source("theme_hee.R")  # copy of docs/theme_hee.R

W_IN <- 7.2  # full journal page width (183 mm)
save_fig <- function(p, name, h) {
  ggsave(paste0(name, ".png"), p, width = W_IN, height = h, dpi = 300, device = ragg::agg_png, bg = "white")
  ggsave(paste0(name, ".pdf"), p, width = W_IN, height = h, device = cairo_pdf, bg = "white")
}
num <- function(x) format(round(x), big.mark = ",", trim = TRUE)
pct <- function(x) paste0(round(x), "%")

d <- read.csv("oa_by_income_v2.csv", colClasses = "character")
d$oa <- d$is_oa == "True"
grp <- d$group

ROWS <- c("All studies with a DOI", "Low and middle income", "High income", "Both", "No income group")
tab <- rbind(data.frame(row = ROWS[1], n = nrow(d), n_oa = sum(d$oa)),
             do.call(rbind, lapply(ROWS[-1], function(g)
               data.frame(row = g, n = sum(grp == g), n_oa = sum(d$oa[grp == g])))))
tab$share <- 100 * tab$n_oa / tab$n
stopifnot(tab$n[1] == 42144, round(tab$share[1]) == 64)
print(tab[, c("row", "n", "n_oa", "share")])

# The three rows the text quotes are full ink; the two remainder rows are muted, so the
# bars still account for every study with a DOI.
tab$label <- c("All studies with a DOI", "Studies on low- and\nmiddle-income countries",
               "Studies on high-income\ncountries", "Studies on both", "No country income group")
tab$label <- factor(tab$label, rev(tab$label))
tab$minor <- tab$row %in% c("Both", "No income group")

long <- rbind(data.frame(tab, status = "Open access", value = tab$share),
              data.frame(tab, status = "Not open access", value = 100 - tab$share))
long$status <- factor(long$status, c("Not open access", "Open access"))
long$fill <- ifelse(long$status == "Not open access", "Not open access",
                    ifelse(long$minor, "Open access (other groups)", "Open access"))
pal <- c("Open access" = hee_cat[["blue"]], "Open access (other groups)" = hee_seq[5],
         "Not open access" = hee_ink$grid)

p <- ggplot(long, aes(value, label, fill = fill)) +
  geom_col(width = 0.66) +
  geom_text(data = tab, aes(x = 2, y = label, label = pct(share),
                            colour = ifelse(minor, "minor", "major")),
            inherit.aes = FALSE, hjust = 0, size = 3, fontface = "bold") +
  geom_text(data = tab, aes(x = 101.5, y = label, label = paste0("n = ", num(n))),
            inherit.aes = FALSE, hjust = 0, size = 2.5, colour = hee_ink$secondary) +
  geom_vline(xintercept = tab$share[1], linewidth = 0.3, linetype = "22", colour = hee_ink$secondary) +
  annotate("text", x = tab$share[1] + 0.8, y = 5.5, label = paste0("all studies: ", pct(tab$share[1])),
           hjust = 0, vjust = 0, size = 2.3, colour = hee_ink$secondary) +
  scale_fill_manual(values = pal, breaks = c("Open access", "Not open access")) +
  scale_colour_manual(values = c(major = "white", minor = hee_ink$primary), guide = "none") +
  scale_x_continuous(labels = function(x) paste0(x, "%"), breaks = seq(0, 100, 25),
                     limits = c(0, 112), expand = c(0, 0)) +
  scale_y_discrete(expand = expansion(add = c(0.6, 1))) +
  labs(title = "Most health financing studies are open access, more so on low- and middle-income countries",
       x = "Share of studies with a DOI", y = NULL,
       caption = paste0("n = ", num(nrow(d)), " studies with a DOI. Income group: World Bank income group of each ",
                        "country studied in the study's publication year; ",
                        "studies on high-income countries study only high-income countries, studies on low- and ",
                        "middle-income countries only low- or middle-income ones; studies on both and studies ",
                        "naming no country (or none with an income group) are shown for completeness.")) +
  theme_hee(grid = "x") +
  theme(panel.grid.major.x = element_blank(), axis.text.y = element_text(lineheight = 1.05))

save_fig(p, "fig_open_access_by_income_v2", 3.3)

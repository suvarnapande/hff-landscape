# make_open_access_figure.R — figure for the manuscript's open-access sentence:
# "Of the 42,144 studies with a DOI, 64% were open access: 73% of those on low- and
#  middle-income countries and 59% of those on high-income countries."
#
# Counted from the raw dataset (docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv), studies with a DOI.
# Income group is the income_level column (the income group of the countries studied):
#   high income            = every country studied is high income            (22,780; 59% open access)
#   low and middle income  = every country studied is low or middle income   (11,845; 73%)
#   both                   = countries from both groups                      (260)
#   no income group        = no country named, or not matched               (7,259)
#
#   fig_open_access_by_income   share open access, all studies with a DOI and by income group
#
# From this folder:
#   Rscript make_open_access_figure.R

.libPaths(c("_rlib", .libPaths()))
source("theme_hee.R")  # copy of docs/theme_hee.R

W_IN <- 7.2  # full journal page width (183 mm)
save_fig <- function(p, name, h) {
  ggsave(paste0(name, ".png"), p, width = W_IN, height = h, dpi = 300, device = ragg::agg_png, bg = "white")
  ggsave(paste0(name, ".pdf"), p, width = W_IN, height = h, device = cairo_pdf, bg = "white")
}
num <- function(x) format(round(x), big.mark = ",", trim = TRUE)
pct <- function(x) paste0(round(x), "%")

raw <- read.csv("../docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv",
                colClasses = "character")[, c("doi", "is_oa", "income_level")]
d <- raw[!is.na(raw$doi) & trimws(raw$doi) != "", ]
d$oa <- d$is_oa == "True"

grp <- vapply(strsplit(ifelse(is.na(d$income_level), "", d$income_level), "; "), function(t) {
  t <- t[t != ""]
  if (!length(t)) "No income group"
  else if (all(t == "HIC")) "High income"
  else if (!any(t == "HIC")) "Low and middle income"
  else "Both"
}, "")

ROWS <- c("All studies with a DOI", "Low and middle income", "High income", "Both", "No income group")
tab <- rbind(data.frame(row = ROWS[1], n = nrow(d), n_oa = sum(d$oa)),
             do.call(rbind, lapply(ROWS[-1], function(g)
               data.frame(row = g, n = sum(grp == g), n_oa = sum(d$oa[grp == g])))))
tab$share <- 100 * tab$n_oa / tab$n
stopifnot(tab$n[1] == 42144, round(tab$share[1]) == 64,
          round(tab$share[tab$row == "Low and middle income"]) == 73,
          round(tab$share[tab$row == "High income"]) == 59)

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
       caption = paste0("n = ", num(nrow(d)), " studies with a DOI. Income group of the countries studied: ",
                        "studies on high-income countries study only high-income countries, studies on low- and ",
                        "middle-income countries only low- or middle-income ones; studies on both and studies ",
                        "naming no country (or none with an income group) are shown for completeness.")) +
  theme_hee(grid = "x") +
  theme(panel.grid.major.x = element_blank(), axis.text.y = element_text(lineheight = 1.05))

save_fig(p, "fig_open_access_by_income", 3.3)

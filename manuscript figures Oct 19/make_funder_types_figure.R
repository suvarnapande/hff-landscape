# make_funder_types_figure.R — figure for the manuscript's funder sentence:
# "Among them, national governments were the largest group (52.5%), followed by universities,
#  hospitals and institutes (22.4%) and foundations and non-profit organizations (21.7%)."
#
# Numbers from the site data, docs/data/funder_types_v5.json (HFF dataset v2.5.1): studies naming
# each type of funder, as a share of the 9,418 studies that report any funder. A study can name
# funders of several types, so the shares sum to more than 100%.
#
#   fig_funder_types   share of funded studies naming each funder type
#
# From this folder:
#   Rscript make_funder_types_figure.R

.libPaths(c("_rlib", .libPaths()))
source("theme_hee.R")  # copy of docs/theme_hee.R

W_IN <- 7.2  # full journal page width (183 mm)
save_fig <- function(p, name, h) {
  ggsave(paste0(name, ".png"), p, width = W_IN, height = h, dpi = 300, device = ragg::agg_png, bg = "white")
  ggsave(paste0(name, ".pdf"), p, width = W_IN, height = h, device = cairo_pdf, bg = "white")
}
num <- function(x) format(round(x), big.mark = ",", trim = TRUE)

ft <- jsonlite::fromJSON("../docs/data/funder_types_v5.json")
d <- data.frame(type = names(ft$studies_by_type), n = unlist(ft$studies_by_type), row.names = NULL)
d$share <- 100 * d$n / ft$n_funded
stopifnot(ft$n_funded == 9418,
          round(d$share[d$type == "National governments"], 1) == 52.5,
          round(d$share[d$type == "Universities, hospitals & institutes"], 1) == 22.4,
          round(d$share[d$type == "Foundations & non-profits"], 1) == 21.7)

d$label <- c("National governments" = "National governments",
             "Universities, hospitals & institutes" = "Universities, hospitals and institutes",
             "Foundations & non-profits" = "Foundations and non-profit organisations",
             "Multilateral & EU bodies" = "Multilateral and EU bodies",
             "Sub-national governments" = "Sub-national governments",
             "Pharmaceutical companies" = "Pharmaceutical companies",
             "Other private companies" = "Other private companies",
             "Unclassified" = "Funder type not classified")[d$type]
# unclassified last, everything else by size
d$label <- factor(d$label, d$label[order(d$type == "Unclassified", -d$n, decreasing = TRUE)])
# The three types the text names are full blue, the other types lighter, unclassified grey.
TOP3 <- c("National governments", "Universities, hospitals & institutes", "Foundations & non-profits")
d$group <- ifelse(d$type %in% TOP3, "top", ifelse(d$type == "Unclassified", "na", "other"))
pal <- c(top = hee_cat[["blue"]], other = hee_seq[4], na = hee_ink$muted)

p <- ggplot(d, aes(share, label, fill = group)) +
  geom_col(width = 0.68) +
  geom_text(aes(label = paste0(sprintf("%.1f", share), "%  (", num(n), ")"),
                fontface = ifelse(group == "top", "bold", "plain")),
            hjust = 0, nudge_x = 0.8, size = 2.5, colour = hee_ink$secondary) +
  scale_fill_manual(values = pal, guide = "none") +
  scale_x_continuous(labels = function(x) paste0(x, "%"), breaks = seq(0, 60, 20),
                     limits = c(0, 66), expand = c(0, 0)) +
  labs(title = "National governments fund half of the studies that report a funder",
       x = paste0("Share of the ", num(ft$n_funded), " studies that report a funder"), y = NULL,
       caption = paste0("n = ", num(ft$n_funded), " studies reporting at least one funder. Bars show the share ",
                        "of these studies naming at least one funder of each type (number of studies in ",
                        "brackets); a study can name funders of several types, so shares sum to more than 100%.")) +
  theme_hee(grid = "x")

save_fig(p, "fig_funder_types", 3.4)

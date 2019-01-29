#!/usr/bin/env python3

import sys
import pickle
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from helpers import (
    ssim_index_to_db, get_abr_cc, pretty_names, pretty_colors)
from collect_data import VIDEO_DURATION


def collect_ssim(d, expt_id_cache, args):
    ssim = {}

    for session in d:
        expt_id = session[-1]

        if not args.emu:
            expt_config = expt_id_cache[int(expt_id)]
            abr_cc = get_abr_cc(expt_config)
        else:
            abr_cc = tuple(expt_id.split('+'))

        if abr_cc not in ssim:
            ssim[abr_cc] = []

        for video_ts in d[session]:
            dsv = d[session][video_ts]
            curr_ssim_index = dsv['ssim_index']

            # append SSIM index
            ssim[abr_cc].append(curr_ssim_index)

    ssim_mean = {}
    ssim_sem = {}

    for abr_cc in ssim:
        ssim_index_mean = np.mean(ssim[abr_cc])
        sem = np.std(ssim[abr_cc]) / np.sqrt(len(ssim[abr_cc]))

        ssim_db_lower = ssim_index_to_db(ssim_index_mean - sem)
        ssim_db_upper = ssim_index_to_db(ssim_index_mean + sem)

        ssim_db_mean = ssim_index_to_db(ssim_index_mean)
        ssim_mean[abr_cc] = ssim_db_mean
        ssim_sem[abr_cc] = (ssim_db_mean - ssim_db_lower,
                            ssim_db_upper - ssim_db_mean)

    return ssim_mean, ssim_sem


def collect_rebuffer(d, expt_id_cache, args):
    total_play = {}
    total_rebuf = {}

    for session in d:
        expt_id = session[-1]

        if not args.emu:
            expt_config = expt_id_cache[int(expt_id)]
            abr_cc = get_abr_cc(expt_config)
        else:
            abr_cc = tuple(expt_id.split('+'))

        if abr_cc not in total_play:
            total_play[abr_cc] = 0
            total_rebuf[abr_cc] = 0

        total_play[abr_cc] += d[session]['play']
        total_rebuf[abr_cc] += d[session]['rebuf']

    rebuffer_rate = {}

    for abr_cc in total_play:
        rebuffer_rate[abr_cc] = total_rebuf[abr_cc] / total_play[abr_cc]

    return rebuffer_rate


def plot_ssim_mean_vs_rebuf_rate(ssim_mean, ssim_sem, rebuffer_rate, args):
    xmin = 0
    xmax = 0.85
    ymin = 15.1
    ymax = 17.1

    for cc in ['bbr', 'cubic']:
        fig, ax = plt.subplots()

        ax.set_xlabel('Time spent stalled (%)')
        ax.set_ylabel('Average SSIM (dB)')

        # Hide the right and top spines
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

        for abr_cc in ssim_mean:
            if abr_cc[1] != cc:
                continue
            abr = abr_cc[0]

            x = rebuffer_rate[abr_cc] * 100  # %
            y = ssim_mean[abr_cc]  # dB
            sem = ssim_sem[abr_cc]
            print(abr_cc, x, y, sem)

            ax.scatter(x, y, color=pretty_colors[abr])
            # error bars are too small
            # ax.errorbar(x, y, yerr=[[sem[0]], [sem[1]]])
            ax.annotate(pretty_names[abr], (x, y))

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.invert_xaxis()

        fig_name = '{}_ssim_rebuffer.svg'.format(cc)
        fig.savefig(fig_name)
        sys.stderr.write('Saved plot to {}\n'.format(fig_name))


def plot(expt_id_cache, args):
    with open(args.video_data_pickle, 'rb') as fh:
        video_data = pickle.load(fh)

    with open(args.buffer_data_pickle, 'rb') as fh:
        buffer_data = pickle.load(fh)

    ssim_mean, ssim_sem = collect_ssim(video_data, expt_id_cache, args)
    rebuffer_rate = collect_rebuffer(buffer_data, expt_id_cache, args)

    plot_ssim_mean_vs_rebuf_rate(ssim_mean, ssim_sem, rebuffer_rate, args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--video-data-pickle', required=True)
    parser.add_argument('-b', '--buffer-data-pickle', required=True)
    parser.add_argument('-e', '--expt-id-cache')
    parser.add_argument('--emu', action='store_true')
    args = parser.parse_args()

    if not args.emu:
        assert(args.expt_id_cache)

        with open(args.expt_id_cache, 'rb') as fh:
            expt_id_cache = pickle.load(fh)

        plot(expt_id_cache, args)
    else:
        # emulation
        plot(None, args)


if __name__ == '__main__':
    main()

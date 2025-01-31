import logging
import ROOT
from .defaults import _name_string, _process_map, _dataset_map
logger = logging.getLogger("")


def replace_negative_entries_and_renormalize(histogram, tolerance):
    # This function is taken from https://github.com/KIT-CMS/shape-producer/blob/beddc4a43e2e326018d804e58d612d8688ec33b6/shape_producer/histogram.py#L189

    # Find negative entries and calculate norm.
    norm_all = 0.0
    norm_positive = 0.0
    for i_bin in range(1, histogram.GetNbinsX() + 1):
        this_bin = histogram.GetBinContent(i_bin)
        if this_bin < 0.0:
            histogram.SetBinContent(i_bin, 0.0)
        else:
            norm_positive += this_bin
        norm_all += this_bin

    if norm_all == 0.0 and norm_positive != 0.0:
        logger.fatal(
            "Aborted renormalization because initial normalization is zero, but positive normalization not. . Check histogram %s",
            histogram.GetName(),
        )
        raise Exception

    if norm_all < 0.0:
        logger.fatal(
            "Aborted renormalization because initial normalization is negative: %f. Check histogram %s ",
            norm_all,
            histogram.GetName(),
        )
        raise Exception

    if abs(norm_all - norm_positive) > tolerance * norm_all:
        logger.warning(
            "Renormalization failed because the normalization changed by %f, which is above the tolerance %f. Check histogram %s",
            abs(norm_all - norm_positive),
            tolerance * norm_all,
            histogram.GetName(),
        )

    # Renormalize histogram if negative entries are found
    if norm_all != norm_positive:
        if norm_positive == 0.0:
            logger.fatal(
                "Renormalization failed because all bins have negative entries."
            )
            raise Exception
        for i_bin in range(1, histogram.GetNbinsX() + 1):
            this_bin = histogram.GetBinContent(i_bin)
            histogram.SetBinContent(i_bin, this_bin * norm_all / norm_positive)

    return histogram


def qcd_estimation(
    rootfile,
    channel,
    selection,
    variable,
    variation="Nominal",
    is_embedding=True,
    is_nlo=False,
    extrapolation_factor=1.0,
    sub_scale=1.0,
):
    logger.debug("Parameters for qcd estimation")
    logger.debug("channel: %s", channel)
    logger.debug("selection: %s", selection)
    logger.debug("variable: %s", variable)
    logger.debug("variation: %s", variation)
    logger.debug("is_embedding: %s", is_embedding)
    logger.debug("extrapolation_factor: %s", extrapolation_factor)
    logger.debug("sub_scale: %s", sub_scale)
    if is_embedding:
        procs_to_subtract = ["EMB", "ZL", "ZJ", "TTL", "TTJ", "VVL", "VVJ", "W"]
        if is_nlo:
            procs_to_subtract = ["EMB", "ZL_NLO", "ZJ", "TTL", "TTJ", "VVL", "VVJ", "W_NLO"]
        if "em" in channel:
            procs_to_subtract = ["EMB", "ZL", "TTL", "VVL", "W"]
            if is_nlo:
                procs_to_subtract = ["EMB", "ZL_NLO", "TTL", "VVL", "W_NLO"]
        elif channel in ["mm", "ee"]:
            if is_nlo:
                procs_to_subtract = ["EMB", "W_NLO"]
            else:
                procs_to_subtract = ["EMB", "W"]
        # elif "et" in channel:
        #     procs_to_subtract = ["EMB", "ZL", "ZJ", "TTL", "TTJ", "VVL", "VVJ"]
    else:
        procs_to_subtract = [
            "ZTT",
            "ZL",
            "ZJ",
            "TTT",
            "TTL",
            "TTJ",
            "VVT",
            "VVL",
            "VVJ",
            "W",
        ]
        if is_nlo:
            procs_to_subtract = [
                "ZTT_NLO",
                "ZL_NLO",
                "ZJ_NLO",
                "TTT",
                "TTL",
                "TTJ",
                "VVT",
                "VVL",
                "VVJ",
                "W_NLO",
            ]
        if "em" in channel:
            procs_to_subtract = ["ZTT", "ZL", "TTT", "TTL", "VVT", "VVL", "W"]
            if is_nlo:
                procs_to_subtract = ["ZTT_NLO", "ZL_NLO", "TTT", "TTL", "VVT", "VVL", "W_NLO"]
        elif channel in ["mm", "ee"]:
            if is_nlo:
                procs_to_subtract = ["ZL_NLO", "W_NLO", "VVL", "TTL"]
            else:
                procs_to_subtract = ["ZL", "W", "VVL", "TTL"]
        # elif "et" in channel:
        #     procs_to_subtract = ["ZTT", "ZL", "TTT", "TTL", "VVT", "VVL"]

    logger.debug(
        "Trying to get object {}".format(
            _name_string.format(
                dataset="data",
                channel=channel,
                process="",
                selection="-" + selection if selection != "" else "",
                variation="same_sign" if "subtrMC" in variation else variation,
                variable=variable,
            )
        )
    )
    base_hist = rootfile.Get(
        _name_string.format(
            dataset="data",
            channel=channel,
            process="",
            selection="-" + selection if selection != "" else "",
            variation="same_sign" if "subtrMC" in variation else variation,
            variable=variable,
        )
    ).Clone()
    for proc in procs_to_subtract:
        logger.debug(
            "Trying to get object {}".format(
                _name_string.format(
                    dataset=_dataset_map[proc],
                    channel=channel,
                    process="-" + _process_map[proc],
                    selection="-" + selection if selection != "" else "",
                    variation="same_sign" if "subtrMC" in variation else variation,
                    variable=variable,
                )
            )
        )
        base_hist.Add(
            rootfile.Get(
                _name_string.format(
                    dataset=_dataset_map[proc],
                    channel=channel,
                    process="-" + _process_map[proc],
                    selection="-" + selection if selection != "" else "",
                    variation="same_sign" if "subtrMC" in variation else variation,
                    variable=variable,
                )
            ),
            -sub_scale,
        )

    proc_name = "QCD" if is_embedding else "QCDMC"
    if is_nlo:
        proc_name = "_".join([proc_name, "NLO"])
    if variation in ["same_sign"]:
        qcd_variation = "Nominal"
    else:
        qcd_variation = variation.replace("same_sign_", "")
    logger.debug(
        "Use extrapolation_factor factor with value %.2f to scale from ss to os region.",
        extrapolation_factor,
    )
    if base_hist.Integral() > 0.0:
        base_hist.Scale(extrapolation_factor)
    else:
        logger.warning(
            "No data in same-sign region for histogram %s. Setting extrapolation factor to 0.0",
            base_hist.GetName(),
        )
        base_hist.Scale(0.0)
    variation_name = (
        base_hist.GetName()
        .replace("data", proc_name)
        .replace(
            variation if "subtrMC" not in variation else "same_sign", qcd_variation
        )
        .replace(channel, "-".join([channel, proc_name]), 1)
    )
    base_hist.SetName(variation_name)
    base_hist.SetTitle(variation_name)
    replace_negative_entries_and_renormalize(base_hist, tolerance=100.05)
    return base_hist


def abcd_estimation(
    rootfile,
    channel,
    selection,
    variable,
    variation="Nominal",
    is_embedding=True,
    transposed=False,
):
    logger.debug("Parameters for abcd estimation")
    logger.debug("channel: %s", channel)
    logger.debug("selection: %s", selection)
    logger.debug("variable: %s", variable)
    logger.debug("variation: %s", variation)
    logger.debug("is_embedding: %s", is_embedding)
    logger.debug("transposed: %s", transposed)
    if variation != "Nominal" and not variation.startswith("abcd_"):
        # add abcd_ on the front of the variation
        variation = "abcd_" + variation
    if is_embedding:
        procs_to_subtract = ["EMB", "ZL", "ZJ", "TTL", "TTJ", "VVL", "VVJ", "W"]
        if "em" in channel:
            procs_to_subtract = ["EMB", "ZL", "TTL", "VVL", "W"]
    else:
        procs_to_subtract = [
            "ZTT",
            "ZL",
            "ZJ",
            "TTT",
            "TTL",
            "TTJ",
            "VVT",
            "VVL",
            "VVJ",
            "W",
        ]
        if "em" in channel:
            procs_to_subtract = ["ZTT", "ZL", "TTT", "TTL", "VVT", "VVL", "W"]

    # Get the shapes from region B.
    logger.debug(
        "Trying to get object {}".format(
            _name_string.format(
                dataset="data",
                channel=channel,
                process="",
                selection="-" + selection if selection != "" else "",
                variation=variation.replace("same_sign_anti_iso", "same_sign")
                if transposed
                else variation.replace("same_sign_anti_iso", "anti_iso"),
                variable=variable,
            )
        )
    )
    base_hist = rootfile.Get(
        _name_string.format(
            dataset="data",
            channel=channel,
            process="",
            selection="-" + selection if selection != "" else "",
            variation=variation.replace("same_sign_anti_iso", "same_sign")
            if transposed
            else variation.replace("same_sign_anti_iso", "anti_iso"),
            variable=variable,
        )
    ).Clone()
    for proc in procs_to_subtract:
        logger.debug(
            "Trying to get object {}".format(
                _name_string.format(
                    dataset=_dataset_map[proc],
                    channel=channel,
                    process="-" + _process_map[proc],
                    selection="-" + selection if selection != "" else "",
                    variation=variation.replace("same_sign_anti_iso", "same_sign")
                    if transposed
                    else variation.replace("same_sign_anti_iso", "anti_iso"),
                    variable=variable,
                )
            )
        )
        base_hist.Add(
            rootfile.Get(
                _name_string.format(
                    dataset=_dataset_map[proc],
                    channel=channel,
                    process="-" + _process_map[proc],
                    selection="-" + selection if selection != "" else "",
                    variation=variation.replace("same_sign_anti_iso", "same_sign")
                    if transposed
                    else variation.replace("same_sign_anti_iso", "anti_iso"),
                    variable=variable,
                )
            ),
            -1.0,
        )
    # Calculate extrapolation_factor from regions C and D.
    data_yield_C = rootfile.Get(
        _name_string.format(
            dataset="data",
            channel=channel,
            process="",
            selection="-" + selection if selection != "" else "",
            variation=variation.replace("same_sign_anti_iso", "anti_iso")
            if transposed
            else variation.replace("same_sign_anti_iso", "same_sign"),
            variable=variable,
        )
    ).Integral()
    bkg_yield_C = sum(
        rootfile.Get(
            _name_string.format(
                dataset=_dataset_map[proc],
                channel=channel,
                process="-" + _process_map[proc],
                selection="-" + selection if selection != "" else "",
                variation=variation.replace("same_sign_anti_iso", "anti_iso")
                if transposed
                else variation.replace("same_sign_anti_iso", "same_sign"),
                variable=variable,
            )
        ).Integral()
        for proc in procs_to_subtract
    )
    data_yield_D = rootfile.Get(
        _name_string.format(
            dataset="data",
            channel=channel,
            process="",
            selection="-" + selection if selection != "" else "",
            variation=variation,
            variable=variable,
        )
    ).Integral()
    bkg_yield_D = sum(
        rootfile.Get(
            _name_string.format(
                dataset=_dataset_map[proc],
                channel=channel,
                process="-" + _process_map[proc],
                selection="-" + selection if selection != "" else "",
                variation=variation,
                variable=variable,
            )
        ).Integral()
        for proc in procs_to_subtract
    )
    if data_yield_C == 0 or data_yield_D == 0:
        logger.warning(
            "No data in region C or region D for shape of variable %s in category %s. Setting extrapolation_factor to zero.",
            variable,
            "-" + selection if selection != "" else "",
        )
        extrapolation_factor = 0.0
    elif not data_yield_D - bkg_yield_D > 0:
        logger.warning(
            "Event content in region D for shape of variable %s in category %s is %f.",
            variable,
            selection if selection != "" else "inclusive",
            data_yield_D - bkg_yield_D,
        )
        extrapolation_factor = 0.0
    else:
        extrapolation_factor = (data_yield_C - bkg_yield_C) / (
            data_yield_D - bkg_yield_D
        )

    proc_name = "QCD" if is_embedding else "QCDMC"
    if variation in ["abcd_same_sign_anti_iso"]:
        qcd_variation = "Nominal"
    else:
        qcd_variation = variation.replace("abcd_same_sign_anti_iso_", "")
    logger.debug(
        "Use extrapolation_factor factor with value %.2f to scale from region B to region A.",
        extrapolation_factor,
    )
    base_hist.Scale(extrapolation_factor)
    variation = (
        variation.replace("abcd_same_sign_anti_iso", "abcd_same_sign")
        if transposed
        else variation.replace("abcd_same_sign_anti_iso", "abcd_anti_iso")
    )
    variation_name = (
        base_hist.GetName()
        .replace("data", proc_name)
        .replace(variation, qcd_variation)
        .replace(channel, "-".join([channel, proc_name]), 1)
    )
    base_hist.SetName(variation_name)
    base_hist.SetTitle(variation_name)
    replace_negative_entries_and_renormalize(base_hist, tolerance=100.05)
    return base_hist

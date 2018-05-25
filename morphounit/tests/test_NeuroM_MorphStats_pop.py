import sciunit
import sciunit.scores as sci_scores
import morphounit.scores as mph_scores
# import morphounit.capabilities as mph_cap
import morphounit.plots as mph_plots

import os
import copy
import json

import neurom as nm

import numpy as np
import quantities


class NeuroM_MorphStats_pop_Test(sciunit.Test):
    """Tests a set of cell's morphological features in a neuronal population"""
    score_type = mph_scores.CombineZScores

    def __init__(self, observation=None, name="NeuroM MorphStats_pop"):

        self.description = "Tests a set of cell's morpho-features in a population of digitally reconstructed neurons"
        # require_capabilities = (mph_cap.ProvidesMorphFeatureInfo,)

        self.figures = []
        observation = self.format_data(observation)
        sciunit.Test.__init__(self, observation, name)

    # ----------------------------------------------------------------------

    def format_data(self, data):
        """
        This accepts data input in the form:
        ***** (observation) *****
        {"cell_kind": { "cell_part_1": {'morph_feature_name_11': {'mean value': 'X11_mean units_str', 'std': 'X11_std units_str'},
                                        'morph_feature_name_12': {'mean value': 'X12_mean units_str', 'std': 'X12_std units_str'},
                                        ... },
                        "cell_part_2": {'morph_feature_name_21': {'mean value': 'X21_mean units_str', 'std': 'X21_std units_str'},
                                        'morph_feature_name_22': {'mean value': 'X22_mean units_str', 'std': 'X22_std units_str'},
                                        ... },
                        ... }
        }
        ***** (prediction) *****
        {"cell1_ID": { 'cell_part_1': {'morph_feature_name_11': {'value': 'X11 units_str'},
                                       'morph_feature_name_12': {'value': 'X12 units_str'},
                                        ... },
                       'cell_part_2': {'morph_feature_name_21': {'value': 'X21 units_str'},
                                       'morph_feature_name_22': {'value': 'X22 units_str'},
                                        ... },
                       ... }
         "cell2_ID": { 'cell_part_1': {'morph_feature_name_11': {'value': 'Y11 units_str'},
                                       'morph_feature_name_12': {'value': 'Y12 units_str'},
                                        ... },
                       'cell_part_2': {'morph_feature_name_21': {'value': 'Y21 units_str'},
                                       'morph_feature_name_22': {'value': 'Y22 units_str'},
                                        ... },
                       ... }
        ... }

        It splits the values of mean, std and value to numeric quantities
        and their units (via quantities package)
        """
        dim_um = ['radius', 'radii', 'diameter', 'length', 'distance', 'extent']
        dim_non = ['order', 'number']
        for dict1 in data.values():  # Dict. with cell's part-features dictionary pairs for each cell
            for dict2 in dict1.values():    # Dict. with feature name-value pairs for each cell part: soma,
                                            # apical_dendrite, basal_dendrite or axon
                for dict3 in dict2.values():  # Dict. with 'value', 'mean' and 'std' values
                    for key, val in dict3.items():
                        quantity_parts = val.split()
                        number, units_str = float(quantity_parts[0]), " ".join(quantity_parts[1:])
                        try:
                            if any(sub_str in key for sub_str in dim_um):
                                assert (units_str == quantities.um | units_str == quantities.mm), \
                                    sciunit.Error("Values not in appropriate format. Required units: mm or um")
                            elif any(sub_str in key for sub_str in dim_non):
                                assert(units_str == quantities.dimensionless), \
                                    sciunit.Error("Values not in appropriate format. Required units: ", quantities.dimensionless)
                        finally:
                            dict3[key] = quantities.Quantity(number, units_str)

        return data

    # ----------------------------------------------------------------------

    def validate_observation(self, observation):
        for dict1 in observation.values():  # Dict. with cell's part-features dictionary pairs for each cell
            for dict2 in dict1.values():    # Dict. with feature name-value pairs for each cell part: soma,
                                            # apical_dendrite, basal_dendrite or axon
                for dict3 in dict2.values():  # Dict. with 'value' or 'mean' and 'std' values
                    for val in dict3.values():
                        assert type(val) is quantities.Quantity, \
                                sciunit.ObservationError(("Observation must be of the form "
                                                          "{'mean': 'XX units_str','std': 'YY units_str'}"))

    # ----------------------------------------------------------------------

    def generate_prediction(self, model, verbose=False):
        """Implementation of sciunit.Test.generate_prediction"""

        self.path_test_output = model.morph_stats_output
        self.morp_path = model.morph_path
        mod_prediction = model.get_morph_feature_info()

        print 'mod_prediction = \n', json.dumps(mod_prediction, sort_keys=True, indent=3)

        # Computing average soma's diameter and following average neurite's (axon and basal dendrite) features:
        # path-length, number of trunks, maximum branch order,
        # field diameter, bounding-box -X,Y,Z- extents, -largest,shortest- principal extents
        mapping = lambda section: section.points
        morph_paths = os.listdir(self.morp_path)
        for morph_path in morph_paths:
            neuron_path = os.path.join(self.morp_path, morph_path)
            neuron_model = nm.load_neuron(neuron_path)
            for dict0 in mod_prediction.values():  # Set of cell's part-features dictionary pairs
                for cell_part, dict1 in dict0.items():  # Dict. with feature name-value pairs for each cell part:
                                                        # soma, apical_dendrite, basal_dendrite or axon
                    for feature_name in dict1.keys():
                        feature_value = nm.get(feature_name, neuron_model, neurite_type=getattr(nm, cell_part.upper()))
                        dict1[feature_name].extend(feature_value)
                        print morph_path, cell_part, feature_name, '\n'

        # Adding more neurite's features:
        # field diameter, bounding-box -X,Y,Z- extents and -largest,shortest- principal extents
        neurite_features_add = ['neurite_X_extent', 'neurite_Y_extent', 'neurite_Z_extent', 'neurite_shortest_extent',
                                'neurite_largest_extent', 'neurite_field_diameter']

        for dict0 in mod_prediction.values():  # Set of cell's part-features dictionary pairs
            for cell_part, dict1 in dict0.values():
                    if any(sub_str in cell_part for sub_str in ['axon', 'dendrite']):
                        dict_features.update({key: {morph_feature: list() for morph_feature in soma_features}})
                    else:
                        dict_features.update({key: {morph_feature: list() for morph_feature in neurite_features}})

        for morph_path in morph_paths:
            neuron_path = os.path.join(self.morp_path, morph_path)
            neuron_model = nm.load_neuron(neuron_path)
            for dict0 in mod_prediction.values():  # Set of cell's part-features dictionary pairs
                for cell_part, dict1 in dict0.items():  # Dict. with feature name-value pairs for each cell part:
                                                        # soma, apical_dendrite, basal_dendrite or axon

                    if any(sub_str in cell_part for sub_str in ['axon', 'dendrite']):
                        filter = lambda neurite: neurite.type == getattr(nm.NeuriteType, cell_part)
                        neurite_points = [p for p in nm.iter_neurites(neuron_model, mapping, filter)]
                        neurite_points = np.concatenate(neurite_points)
                        neurite_cloud = neurite_points[:, 0:3]

                        # Compute the neurite's bounding-box -X,Y,Z- extents
                        neurite_X_extent, neurite_Y_extent, neurite_Z_extent = \
                            np.max(neurite_cloud, axis=0) - np.min(neurite_cloud, axis=0)
                        dict1["neurite_X_extent"].append(neurite_X_extent)
                        dict1["neurite_Y_extent"].append(neurite_Y_extent)
                        dict1["neurite_Z_extent"].append(neurite_Z_extent)

                        # Compute the neurite's -largest, shortest- principal extents
                        principal_extents = sorted(nm.morphmath.principal_direction_extent(neurite_cloud))
                        dict1["neurite_shortest_extent"].append(principal_extents[0])
                        dict1["neurite_largest_extent"].append(principal_extents[-1])

                        # Compute the neurite-field diameter
                        neurite_field_diameter = nm.morphmath.polygon_diameter(neurite_cloud)
                        dict1["neurite_field_diameter"].append(neurite_field_diameter)

        """
        total_neurite_length
        total_number_of_neurite
        max_section_branch_order
        """

        print 'mod_prediction = \n', json.dumps(mod_prediction, sort_keys=True, indent=3)

        # Adding the right units and converting feature values to strings
        dim_um = ['radius', 'radii', 'diameter', 'length', 'distance', 'extent']
        for dict1 in mod_prediction.values():  # Set of cell's part-features dictionary pairs for each cell
            for dict2 in dict1.values():  # Dict. with feature name-value pairs for each cell part:
                                            # soma, apical_dendrite, basal_dendrite or axon
                for key, val in dict2.items():
                    if any(sub_str in key for sub_str in ['radius', 'radii']):
                        del dict2[key]
                        val *= 2
                        key = key.replace("radius", "diameter")
                        key = key.replace("radii", "diameter")
                    if any(sub_str in key for sub_str in dim_um):
                        dict2[key] = dict(value=str(val) + ' um')
                    else:
                        dict2[key] = dict(value=str(val))

        self.prediction_txt = copy.deepcopy(mod_prediction)

        # prediction = self.format_data(mod_prediction)
        # return prediction

    # ----------------------------------------------------------------------

    def compute_score(self, observation, prediction, verbose=True):
        """Implementation of sciunit.Test.score_prediction"""

        self.observation = observation
        self.prediction = prediction

        # Computing the scores
        cell_t = observation.keys()[0]  # Cell type

        score_cell_dict = dict.fromkeys([key0 for key0 in prediction.keys()], [])
        obs_features = copy.deepcopy(observation.values())[0]  # only features registered in observation data are tested
        score_feat_dict = dict()
        for key0 in prediction:  # cell_ID keys

            score_feat_dict.update({key0: obs_features})
            scores_cell_list = list()
            for key1 in score_feat_dict[key0]:  # cell's part: soma, axon, apical_dendrite or basal_dendrite
                for key2 in score_feat_dict[key0][key1]:  # features names

                        score_feat_value = sci_scores.ZScore.compute(observation[cell_t][key1][key2],
                                                                     prediction[key0][key1][key2]).score
                        scores_cell_list.extend([score_feat_value])

                        score_feat_dict[key0][key1][key2] = {"score": score_feat_value}

            Mean_Zscore_dict = {"A mean |Z-score|": mph_scores.CombineZScores.compute(scores_cell_list).score}
            score_feat_dict[key0].update(Mean_Zscore_dict)
            score_cell_dict[key0] = Mean_Zscore_dict

        self.score_cell_dict = score_cell_dict
        self.score_feat_dict = score_feat_dict

        # Taking the average of the cell's scores as the overall score for the Test
        mean_score = np.mean([dict1["A mean |Z-score|"] for dict1 in score_cell_dict.values()])
        self.score = mph_scores.CombineZScores(mean_score)
        self.score.description = "A mean |Z-score|"

        # ---------------------- Saving relevant results ----------------------
        # create output directory
        # Currently done inside the model Class
        """
        if not os.path.exists(self.path_test_output):
            os.makedirs(self.path_test_output)
        """
        # Saving json file with model predictions
        json_pred_file = mph_plots.jsonFile_MorphStats(testObj=self, dictData=self.prediction_txt,
                                                       prefix_name="prediction_summary_")
        json_pred_files = json_pred_file.create()
        self.figures.extend(json_pred_files)

        # Saving json file with scores
        json_scores_file = mph_plots.jsonFile_MorphStats(testObj=self, dictData=self.score_feat_dict,
                                                         prefix_name="scores_summary_")
        json_scores_files = json_scores_file.create()
        self.figures.extend(json_scores_files)

        # Saving table with results
        txt_table = mph_plots.TxtTable_MorphStats(self)
        table_files = txt_table.create()
        self.figures.extend(table_files)

        # Saving figure with scores bar-plot
        barplot_figure = mph_plots.ScoresBars_MorphStats(self)
        barplot_files = barplot_figure.create()
        self.figures.extend(barplot_files)

        return self.score

    def bind_score(self, score, model, observation, prediction):
        score.related_data["figures"] = self.figures
        return score
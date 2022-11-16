from pandas import DataFrame


def ratio(df: DataFrame, feature: str) -> DataFrame:
    """
    Calculate the class distribution ratio of a feature by using the feature with the least samples as the basis
    for the calculation
    :param df: dataframe
    :param feature: which feature should be used for grouping
    :return: ratio for each characteristic
    """
    g = df.groupby([feature]).size().to_frame(name="samples")
    min_samples = g.iloc[:, 0].min()
    g['ratio'] = round(g.iloc[:, 0] / min_samples, 1)
    return g

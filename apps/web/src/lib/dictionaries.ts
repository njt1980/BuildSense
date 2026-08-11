import en from "./dictionaries/en.json";
import hi from "./dictionaries/hi.json";
import kn from "./dictionaries/kn.json";
import ta from "./dictionaries/ta.json";
import ml from "./dictionaries/ml.json";

const dictionaries: Record<string, any> = {
  en,
  hi,
  kn,
  ta,
  ml,
};

export const getDictionary = (locale: string) => {
  return dictionaries[locale] || dictionaries.en;
};

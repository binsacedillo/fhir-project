export type Patient = {
  id: string;
  identifier?: { value?: string }[];
  name?: { text?: string; given?: string[]; family?: string }[];
  birthDate?: string;
  active?: boolean;
};

export type AllergyIntolerance = {
  code?: { text?: string; coding?: { display?: string }[] };
  criticality?: string;
  type?: string;
};

export type MedicationStatement = {
  medicationCodeableConcept?: { text?: string; coding?: { display?: string }[] };
  status?: string;
};

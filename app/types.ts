export type LicenseStatus = "Active" | "Expired" | "Revoked" | "Canceled" | "Surrendered";
export type LicenseType = "Retailer" | "Microbusiness" | "Distributor" | "Other";
export type LicenseDesignation = "Adult-Use" | "Medicinal" | "Adult-Use and Medicinal";
export type BusinessStructure = "LLC" | "Corporation" | "Sole Proprietorship" | "Partnership" | "Other";

export interface DispensaryData {
  first_names: string;
  business_legal: string;
  business_dba: string;
  city: string;
  state: string;
  zip: string;
  address: string;
  license_status: LicenseStatus;
  license_type: LicenseType;
  license_designation: LicenseDesignation;
  issue_date: string;
  expiration_date: string;
  business_structure: BusinessStructure;
  owner_names: string;
  activity: string;
  email: string;
  phone: string;
}

export interface GeneratedSequence {
  diagnosis_problem: string;
  diagnosis_revenue: string;
  email1_subject: string;
  email1_body: string;
  email2_subject: string;
  email2_body: string;
  email3_subject: string;
  email3_body: string;
  sms1: string;
  sms2: string;
  sms3: string;
  raw: string;
}

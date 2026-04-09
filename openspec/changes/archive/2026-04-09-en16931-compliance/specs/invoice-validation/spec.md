# Invoice Validation

## MODIFIED Requirements

### Requirement: Basic structural validation

The validator MUST check for all mandatory EN-16931 elements in addition to the
original five.

#### Scenario: Missing EN-16931 mandatory elements

- **WHEN** XML bytes are missing any mandatory EN-16931 element (CustomizationID, ProfileID, InvoiceTypeCode, DocumentCurrencyCode, LegalMonetaryTotal, TaxTotal, EndpointID, PostalAddress, PartyLegalEntity)
- **THEN** a FATAL rule is returned for each missing element

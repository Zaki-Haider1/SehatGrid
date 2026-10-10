# Islamabad hospital directory research

Sources checked: **10 October 2026**. This is a curated initial directory of 12 hospitals, not an exhaustive city census. The scoped MVP uses the first eight records as labelled public location context for synthetic partners; the full 12-record research register remains here for provenance.

## Method and accuracy

Hospital/government pages supply addresses, business contact numbers, published hours and selected service descriptions. OpenStreetMap hospital objects supply 11 coordinate points; Federal General Hospital uses the coordinate printed in its own contact-page map. Names and addresses were compared to avoid confusing a campus with a bus stop, dispensary or similarly named hospital.

Points represent mapped hospital buildings/campuses. Their decimal precision does not establish survey accuracy or a verified entrance. Access restrictions, hours, contact details and current services should be confirmed directly with each hospital. The map uses longitude/latitude in geographic coordinates; it does not calculate driving directions, travel time or clinical suitability.

Real directory facts are separate from synthetic service slots, requests, costs and budgets. A missing capacity row means no demo capacity was reported, not that a real hospital is full or lacks a service. No facility partnership or acceptance of platform referrals is claimed.

The cardinal Central/East/South/West/North fields are five **demonstration planning catchments**, not official ICT zones or sector boundaries. Actual sectors are profile fields and pins use researched physical coordinates.

## Locations and source register

| Hospital | Sector/locality | Type | Latitude, longitude | Published main phone | Coordinate evidence | Directory evidence |
|---|---|---|---|---|---|---|
| Shifa International Hospital | H-8/4 | Private | 33.6754770, 73.0664514 | +92 51 8464646 | [Point source](https://www.openstreetmap.org/relation/8103951) | [Hospital contact](https://shifa.com.pk/contact-us), [Emergency department](https://www.shifa.com.pk/specialities/emergency-medicine/islamabad), [Ambulance service](https://shifa.com.pk/shifa-ambulance-service) |
| Pakistan Institute of Medical Sciences (PIMS) | G-8/3 | Public | 33.7022691, 73.0525291 | +92 51 9261170 | [Point source](https://www.openstreetmap.org/way/22328601) | [Hospital contact](https://pims.gov.pk/contactus.php), [Hospital components and specialties](https://pims.gov.pk/about.php), [Clinical services](https://pims.gov.pk/ISBhospital.php) |
| Federal Government Polyclinic | G-6/2 | Public | 33.7211006, 73.0828053 | +92 51 9218300 | [Point source](https://www.openstreetmap.org/node/253018400) | [Hospital contact and hours](https://www.fgpc.gov.pk/contact), [Hospital overview](https://fgpc.gov.pk/aboutus) |
| Kulsum International Hospital | Blue Area | Private | 33.7180912, 73.0727516 | +92 51 8446666 | [Point source](https://www.openstreetmap.org/node/4954775564) | [Hospital website and contact](https://kih.com.pk/), [Hospital location](https://kih.com.pk/slide/kulsum-international-hospital/) |
| Maroof International Hospital | F-10 Markaz | Private | 33.6974652, 73.0118292 | +92 51 111644911 | [Point source](https://www.openstreetmap.org/way/556277383) | [Hospital contact](https://maroof.com.pk/contact), [ICT hospital directory](https://ictadministration.gov.pk/education-and-health/) |
| Ali Medical Centre | F-8 Markaz | Private | 33.7104738, 73.0417644 | +92 51 8090200 | [Point source](https://www.openstreetmap.org/node/240218764) | [Hospital services and contact](https://alimedical.org/), [ICT hospital directory](https://ictadministration.gov.pk/education-and-health/) |
| Capital Hospital (CDA) | G-6/2 | Public | 33.7166093, 73.0799881 | +92 51 9221334 | [Point source](https://www.openstreetmap.org/way/23635809) | [CDA hospital information](https://www.cda.gov.pk/administrationWing), [Government procurement address](https://epms.ppra.gov.pk/public/tenders/tender-details/TS0000009847E) |
| NORI Atomic Energy Cancer Hospital | G-8/3 | Public | 33.6986506, 73.0537462 | +92 51 9260611 | [Point source](https://www.openstreetmap.org/node/12401427423) | [Hospital contact and hours](https://noriaech.gov.pk/Contacts), [ICT hospital directory](https://ictadministration.gov.pk/education-and-health/) |
| NESCOM Hospital | H-11/4 | Public | 33.6481791, 73.0170747 | +92 51 9017100 | [Point source](https://www.openstreetmap.org/way/270104398) | [ICT hospital directory](https://ictadministration.gov.pk/education-and-health/) |
| Quaid-e-Azam International Hospital | H-13 / Golra Morr | Private | 33.6250868, 72.9731560 | +92 51 8449100 | [Point source](https://www.openstreetmap.org/way/235084098) | [Hospital contact](https://www.qih.com.pk/contact), [Hospital services](https://www.qih.com.pk/index.php?Itemid=27&id=3&option=com_content&view=article) |
| KRL General Hospital | G-9/1 | Public | 33.6776437, 73.0318287 | +92 51 9106270 | [Point source](https://www.openstreetmap.org/node/4889677811) | [ICT hospital directory](https://ictadministration.gov.pk/education-and-health/) |
| Federal General Hospital | Chak Shahzad | Public | 33.6844167, 73.1381667 | +92 51 9255561 | [Point source](https://www.fgh.gov.pk/contact.php) | [Hospital contact, map and hours](https://www.fgh.gov.pk/contact.php), [Hospital departments](https://www.fgh.gov.pk/) |

## Decisions and remaining verification

- Capital Hospital: the ICT list says G-6/3, while CDA and a government procurement address say G-6/2. CDA takes precedence; the mapped campus matches G-6/2.
- Polyclinic: the hospital postal address is Luqman Hakeem Road, G-6/2; its OSM object has a different bordering-street label. The campus position is retained, not a guessed address centroid.
- Federal General Hospital: its official embed prints 33°41′03.9″N 73°08′17.4″E. Those coordinates are converted to decimal degrees; the embed viewport centre is deliberately not treated as the hospital pin.
- Shifa: use the hospital campus relation rather than creating duplicate markers for its individual building and campus.
- NESCOM: use the mapped hospital building instead of its second nearby point. Eligibility, services and hours need hospital confirmation.
- Quaid-e-Azam International Hospital: include the western-edge campus using its hospital-published Islamabad address; it lies near Rawalpindi.
- Kulsum and Maroof: omit inconsistent or unconfirmed opening hours/department lists instead of inferring them. Emergency information is included only where the selected source supports it.
- PAF and HBS were researched but not plotted in this initial set: a clearly matched campus/contact source pair was not sufficiently established. Add further hospitals through the same verification process.

## Maintenance, licensing and integration

The versioned dataset is `backend/app/data/islamabad_hospitals.json`. Each record contains its stable source key, coordinates, source URLs, check date, address, public/private classification and uncertainty notes. Scope-v1 reset creates eight synthetic partners using these sourced campus points. Public names/coordinates do not imply partnership. Legacy workflow tables remain historical; the new scoped state is separate.

Research is cached during development; there is no runtime geocoding or repeated Nominatim search on each visit. OpenStreetMap-derived locations and base map are credited to [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), with underlying OSM data subject to ODbL. Hospital source links identify the origin of contact/service facts. Preserve attribution and source provenance in exports and derivative datasets.

The default demo uses a bundled coordinate layer with no tile download. Optional street context uses standard raster tiles and visible attribution, ordinary browser HTTP caching, and no offline/bulk tile downloads. Configure another provider for production traffic according to the [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/). The interactive map uses WebGL; an SVG coordinate-pin fallback and source links remain available if rendering fails.

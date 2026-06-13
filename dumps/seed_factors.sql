--
-- PostgreSQL database dump
--

\restrict QSjZIkbAMwpZOOv7elyOCPsfZwd6O6IRBnYh57cz6s2F7apcP4ZfxS3d2LWkord

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: accident_rate; Type: TABLE DATA; Schema: public; Owner: -
--

SET SESSION AUTHORIZATION DEFAULT;

ALTER TABLE public.accident_rate DISABLE TRIGGER ALL;

COPY public.accident_rate (id, mode, deaths, involved) FROM stdin;
1	car	9	2592
2	moto	43	4234
3	bike	5	135
4	walk	43	215
5	bus	43	221
\.


ALTER TABLE public.accident_rate ENABLE TRIGGER ALL;

--
-- Data for Name: crime_rate; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.crime_rate DISABLE TRIGGER ALL;

COPY public.crime_rate (id, mode, robberies) FROM stdin;
1	walk	10345
2	bike	21
3	moto	3651
4	car	3651
5	bus	229
\.


ALTER TABLE public.crime_rate ENABLE TRIGGER ALL;

--
-- Data for Name: flood_risk_streets; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.flood_risk_streets DISABLE TRIGGER ALL;

COPY public.flood_risk_streets (id, street_name, rain_multiplier, tide_multiplier) FROM stdin;
1	Avenida Agamenon Magalhães	1.6	1.4
2	Avenida Mascarenhas de Morais	1.5	1.3
\.


ALTER TABLE public.flood_risk_streets ENABLE TRIGGER ALL;

--
-- Data for Name: fuel_consumption; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.fuel_consumption DISABLE TRIGGER ALL;

COPY public.fuel_consumption (id, mode, km_per_liter, fixed_cost_per_km) FROM stdin;
1	car	12.5	0
2	moto	30	0
4	walk	0	0
3	bike	0	0
\.


ALTER TABLE public.fuel_consumption ENABLE TRIGGER ALL;

--
-- Data for Name: tide_factors; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.tide_factors DISABLE TRIGGER ALL;

COPY public.tide_factors (id, tide_level, factor) FROM stdin;
1	low	1
2	normal	1.1
3	high	1.3
4	very_high	1.5
\.


ALTER TABLE public.tide_factors ENABLE TRIGGER ALL;

--
-- Data for Name: transport_speed; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.transport_speed DISABLE TRIGGER ALL;

COPY public.transport_speed (id, mode, speed_kmh) FROM stdin;
1	walk	5
2	bike	15
3	car	40
4	moto	45
5	bus	25
6	uber_car	35
7	uber_moto	40
\.


ALTER TABLE public.transport_speed ENABLE TRIGGER ALL;

--
-- Data for Name: uber_price_ranges; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.uber_price_ranges DISABLE TRIGGER ALL;

COPY public.uber_price_ranges (id, service, base_fare, km_min, km_max, min_min, min_max) FROM stdin;
1	uber_car	3	1.1	1.6	0.2	0.4
2	uber_moto	2	0.6	1	0.05	0.2
\.


ALTER TABLE public.uber_price_ranges ENABLE TRIGGER ALL;

--
-- Data for Name: weather_factors; Type: TABLE DATA; Schema: public; Owner: -
--

ALTER TABLE public.weather_factors DISABLE TRIGGER ALL;

COPY public.weather_factors (id, condition, factor) FROM stdin;
1	clear	1
2	light_rain	1.2
3	moderate_rain	1.5
4	heavy_rain	2
5	storm	2.5
\.


ALTER TABLE public.weather_factors ENABLE TRIGGER ALL;

--
-- Name: accident_rate_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.accident_rate_id_seq', 5, true);


--
-- Name: crime_rate_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.crime_rate_id_seq', 5, true);


--
-- Name: flood_risk_streets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.flood_risk_streets_id_seq', 2, true);


--
-- Name: fuel_consumption_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.fuel_consumption_id_seq', 4, true);


--
-- Name: tide_factors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tide_factors_id_seq', 4, true);


--
-- Name: transport_speed_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.transport_speed_id_seq', 7, true);


--
-- Name: uber_price_ranges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.uber_price_ranges_id_seq', 2, true);


--
-- Name: weather_factors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.weather_factors_id_seq', 5, true);


--
-- PostgreSQL database dump complete
--

\unrestrict QSjZIkbAMwpZOOv7elyOCPsfZwd6O6IRBnYh57cz6s2F7apcP4ZfxS3d2LWkord


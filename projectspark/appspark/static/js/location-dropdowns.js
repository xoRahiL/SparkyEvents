/**
 * Cascading Country -> State -> City dropdown, powered by the free,
 * no-key CountriesNow API (https://countriesnow.space). No local dataset
 * to maintain, and it works for any country - not just India - so this is
 * ready to go international whenever needed, just by changing the default
 * selected country below.
 *
 * Usage: call initLocationDropdowns() with the IDs of your three <select>
 * elements. State and City start disabled and populate automatically once
 * their parent selection is made.
 */

const COUNTRIES_API_BASE = 'https://countriesnow.space/api/v0.1/countries';
const DEFAULT_COUNTRY = 'India'; // change this (or make it user-selectable) when going international

function initLocationDropdowns(config) {
    const countrySelect = document.getElementById(config.countryId);
    const stateSelect = document.getElementById(config.stateId);
    const citySelect = document.getElementById(config.cityId);

    // Preselect values, if the form is being used to edit an existing record
    // (e.g. update_event, or a profile that already has a saved address).
    // Read from data-initial="" attributes on the select elements themselves.
    const initialState = stateSelect.dataset.initial || '';
    const initialCity = citySelect.dataset.initial || '';

    function setOptions(select, items, placeholder) {
        select.innerHTML = '';
        const placeholderOption = document.createElement('option');
        placeholderOption.value = '';
        placeholderOption.textContent = placeholder;
        placeholderOption.disabled = true;
        placeholderOption.selected = true;
        select.appendChild(placeholderOption);
        items.forEach(function (item) {
            const opt = document.createElement('option');
            opt.value = item;
            opt.textContent = item;
            select.appendChild(opt);
        });
    }

    function loadStates(country, preselect) {
        stateSelect.disabled = true;
        citySelect.disabled = true;
        setOptions(stateSelect, [], 'Loading states...');

        fetch(COUNTRIES_API_BASE + '/states', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ country: country }),
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.error || !data.data || !data.data.states) {
                    setOptions(stateSelect, [], 'Could not load states - type manually below');
                    return;
                }
                const stateNames = data.data.states.map(function (s) { return s.name; });
                setOptions(stateSelect, stateNames, 'Select a state');
                stateSelect.disabled = false;

                if (preselect && stateNames.includes(preselect)) {
                    stateSelect.value = preselect;
                    loadCities(country, preselect, initialCity);
                }
            })
            .catch(function () {
                setOptions(stateSelect, [], 'Could not load states - type manually below');
            });
    }

    function loadCities(country, state, preselect) {
        citySelect.disabled = true;
        setOptions(citySelect, [], 'Loading cities...');

        fetch(COUNTRIES_API_BASE + '/state/cities', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ country: country, state: state }),
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.error || !data.data) {
                    setOptions(citySelect, [], 'Could not load cities - type manually below');
                    return;
                }
                setOptions(citySelect, data.data, 'Select a city');
                citySelect.disabled = false;

                if (preselect && data.data.includes(preselect)) {
                    citySelect.value = preselect;
                }
            })
            .catch(function () {
                setOptions(citySelect, [], 'Could not load cities - type manually below');
            });
    }

    // Country is fixed to India for now (see DEFAULT_COUNTRY above), but the
    // dropdown is already wired so switching to a country selector later is
    // a small change, not a rebuild.
    if (countrySelect) {
        countrySelect.value = DEFAULT_COUNTRY;
    }
    loadStates(DEFAULT_COUNTRY, initialState);

    stateSelect.addEventListener('change', function () {
        loadCities(DEFAULT_COUNTRY, stateSelect.value, '');
    });
}
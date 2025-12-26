import React, {useState, useEffect} from "react";
import {Alert} from 'react-native';
import AsyncStorage from "@react-native-async-storage/async-storage";


interface Data {
    id: string;
    homeTeam: string;
    awayTeam: string;
    matchDate: string;
    league: string;
    homeForm: string;
    awayForm: string;
    result: 'Home Win' | 'Draw' | 'Away Win' | '';
    homeScore: number;
    awayScore: number;
}

export const SaveMatchData = () => {
    const [homeTeam, setHomeTeam] = useState('');
    const [awayTeam, setAwayTeam] = useState('');
    const [matchDate, setMatchDate] = useState('');
    const [league, setLeague] = useState('');
    const [homeForm, setHomeForm] = useState('');
    const [awayForm, setAwayForm] = useState('');
    const [result, setResult] = useState<'Home Win' | 'Draw' | 'Away Win' | ''>('');
    const [homeScore, setHomeScore] = useState('');
    const [awayScore, setAwayScore] = useState('');
    const [dataset, setDataset] = useState<Data[]>([]);

    useEffect(() => {
        loadDataset();
    }, []);

    const loadDataset = async () => {
        try {
            const data = await AsyncStorage.getItem('footballDataset');
            if (data) {
                setDataset(JSON.parse(data));
            }
        } catch (error) {
            console.error('Error loading dataset: ', error);
        }
    };

    const saveDataset = async (newDataset: Data[]) => {
        try {
            await AsyncStorage.setItem('footballDataset', JSON.stringify(newDataset));
            setDataset(newDataset);
        } catch (error) {
            console.error('Error saving dataset: ', error);
            Alert.alert('Error', 'Failed to save data');
        }
    };

    const handleAddMatch = () => {
        if ()
    }

}
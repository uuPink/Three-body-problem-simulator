import h5py
import pandas as pd
import numpy as np
import os
import shutil
from time import time

#Använd HDF5 för lagring av stora listor d.v.s. simuleringskoordinaterna.
#Parquet används för lagring av mindre data, d.v.s. simuleringens parametrar.
#   Parquet läses m.h.a. pandas medan hdf5 har en egen modul h5.

class DataManager:
    def __init__(self, hdf5file = "sim_data.h5", parquetfile="sim_metadata.parquet", reset = False, storage_limit = 10, backup_freq = 1000, last_sim_override = -10):
        """
        Only use last_sim_override if you want to set the last sim ID to something specific. Remember that datamgr always saves a sim as last_sim_id+1.
        """
        
        self.HDF5 = hdf5file
        self.PARQUET = parquetfile

        self.last_sim_id = None

        self.storage_limit = storage_limit
        self.sim_storage = []

        self.save_time = []

        self.backup_freq = backup_freq
        self.sims_ran_since_backup = 0
    
        #Create files if not exists or if reset mode, and get/set last sim_id
        if reset or not os.path.exists(self.HDF5) or not os.path.exists(self.PARQUET):
            print("Files not found or reset activated, reseting...")
            self.reset()
        else:
            if pd.read_parquet(self.PARQUET).empty:
                self.last_sim_id = 0
                self.last_track = 0
            else:
                df = pd.read_parquet(self.PARQUET, columns=["sim_id"])
                self.last_sim_id = df["sim_id"].iloc[-1]
                try:
                    df = pd.read_parquet(self.PARQUET, columns=["sim_track"])
                    self.last_track = int(df["sim_track"].iloc[-1])
                except:
                    self.last_track = "Null"
        
        if last_sim_override != -10:
            self.last_sim_id = last_sim_override

    def saveSim(self, mode, simtrack, simstart, simend, lifespan, args: tuple, savemode = 0):
        #Simtrack: identifier for which starting system was used for the continued tree of simulations.
        #Lifespan: calculated lifespan of system
        #args: set up by bodymgr. (trajectories, velocities, steps, [...])

        #Mode determines if z coordinate, position and start velocity should be included in saved data or not. Mode = 2 is default (2 as in 2d)
        #velocities always come as 2d-data but still needs flattening.
        t = time()
        self.last_sim_id+=1
        self.sims_ran_since_backup+=1
        
        if mode==2:
            #Förmodligen den bästa list-comprehension jag sett (kan bli ännu bättre dock om du slår ihop enumerate:en in i den andra list-comprehension:en)
            trajectories_flat = [enum[1] for enum in enumerate([trajectoryline for trajectory in args[0] for trajectoryline in trajectory]) if enum[0] not in (2,5,8)]
            start_pos = [enum[1] for enum in enumerate([coordinate for position in args[3] for coordinate in position]) if enum[0] not in (2,5,8)]
            start_vel = [enum[1] for enum in enumerate([velocity for velocities in args[4] for velocity in velocities]) if enum[0] not in (2,5,8)]
        else: 
            trajectories_flat = [trajectoryline for trajectory in args[0] for trajectoryline in trajectory]
            start_pos = [coordinate for position in args[3] for coordinate in position]
            start_vel = [velocity for velocities in args[4] for velocity in velocities]

        velocities_flat = [velocities for velocity in args[1] for velocities in velocity]

        if simtrack != None and simtrack != self.get_last_sim_track():
            self.last_track = simtrack

        metadata = {
            "sim_id": self.last_sim_id,
            "sim_track": simtrack,
            "sim_start": simstart,
            "sim_end": simend,
            "lifespan": lifespan,
            "steps": args[2],
            "start_position": start_pos,
            "start_velocity": start_vel,
            "mass": args[5],
            "radius": args[6],
            "color": args[7],
            "label": args[8],
        }

        #None values are to be removed from metadata before writing. Will appear as NULL if the columns are enabled by values not NULL.
        if simtrack == None:
            metadata.pop("sim_track")
        if lifespan == None:
            metadata.pop("lifespan")

        #Mode 0: save single run
        #Mode 1: bulk save storage_limit amount of sims every storage_limit:th sim 
        if savemode == 0:
            saveToParquet(filename=self.PARQUET, datadict=metadata)
            saveToHDF5(filename=self.HDF5, datalist=(trajectories_flat, velocities_flat), sim_id=self.last_sim_id)
            save_time = time()-t
            self.save_time.append(save_time)
            print("Sim", self.last_sim_id, "saved in", save_time, "seconds")
        else:
            #Add most recent sim
            self.sim_storage.append([self.last_sim_id, metadata, trajectories_flat, velocities_flat])

            if len(self.sim_storage) == self.storage_limit:
                t = time()
                
                bulksaveToParquet(filename=self.PARQUET, datadicts=[sim[1] for sim in self.sim_storage])
                bulksaveToHDF5(filename=self.HDF5, datalists=[(sim[2],sim[3]) for sim in self.sim_storage], sim_ids=[sim[0] for sim in self.sim_storage])
                save_time = time()-t
                self.save_time.append(save_time)
                print("Sim(s)", [sim[0] for sim in self.sim_storage], "saved in", save_time, "seconds")

                self.sim_storage = []
        
        if self.sims_ran_since_backup == self.backup_freq:
            #Backup in case file opening/closing results in fail later on.
            self.backupSim()
            self.sims_ran_since_backup = 0
    
    def backupSim(self, hdf5=True, parquet=True):
        if hdf5:
            shutil.copy2(self.HDF5, f'{self.HDF5}_backup_{time()}.h5')
            print("Backup generated for HDF5")
        if parquet:
            shutil.copy2(self.PARQUET, f'{self.PARQUET}_backup_{time()}.parquet')
            print("Backup generated for parquet")

    def reset(self):
        print("Creating new files...")
        self.reset_hdf5()
        self.reset_parquet()
        self.last_sim_id = 0
        self.last_track = 0

    def reset_hdf5(self):
        try:
            os.remove(self.HDF5)
        except:
            pass

        with h5py.File(self.HDF5, "w") as f:
                f.create_group("simulations")
    def reset_parquet(self):
        try:
            os.remove(self.PARQUET)
        except:
            pass

        df = pd.DataFrame(columns=["sim_id"])
        df.to_parquet(self.PARQUET)
    
    def get_analyze_data(self, sim_id: list | str = 0, gettrajectorydata = True, getvelocitydata = True, getmetadata = True, metadata: list | str = "all", sim_track: int = -10, orderMode = False):
        """
        Docstring for get_analyze_data
        
        :param sim_id: sim_id for simulation to get data from. Default 0 => latest sim
        :type sim_id: list | str
        :param metadata: columns from which to collect metadata. Default "all", example ("start_velocity",). "sim_id" included at default.
        :type metadata: list | str
        :param sim_track: sim_track to retrieve all data from. Enable by putting sim_id != -10. Supports both metadata and trajectories but 50/50 on if it works to get just the trajectories and not the metadata.
        :type sim_track: int

        Metadata and sim_id has to be put in arrays (except for when using "all"). If not parquet won't read correctly. (okay might not be true for sim_id since this function automatically turns single integer into array)
        If sim_track is used you should always include "lifespan" in the metadata to be retrieved as well as the variable you want to look at.    
        """
        #if sim_id[-1]>self.last_sim_id or sim_id[-1]==0: return "Error", "sim_id not in saved data"

        #return_data = [[trajectory, velocity], metadata]

        if sim_track != -10:
            if sim_track == 0: 
                sim_track = self.get_last_sim_track(); 
            if sim_track == "Null": 
                print("No sim_track found.")
                return

            return_data = []
            if getmetadata:
                return_data.append(readParquet(self.PARQUET, sim_track=sim_track, columns=metadata))

            if gettrajectorydata and getmetadata:
                return_data.append(readHDF5(self.HDF5, sim_id=return_data[0]["sim_id"], sim_track=sim_track, hasSimIDs=True, orderMode=orderMode))

            elif gettrajectorydata and not getmetadata:
                return_data.append(readHDF5(self.HDF5, sim_track=sim_track, hasSimIDs=False))
            return return_data

        if not sim_id or sim_id == 0: sim_id = [int(self.get_last_sim_id()),]

        if type(sim_id) != list and sim_id != 0 and sim_id != "all": sim_id=[sim_id,]

        t = time()
        return_data = []
        if gettrajectorydata and not getvelocitydata: return_data.append(readHDF5(self.HDF5, mode = 0, sim_id=sim_id));
        elif gettrajectorydata and getvelocitydata: return_data.append(readHDF5(self.HDF5, mode = 2, sim_id=sim_id, orderMode=orderMode));
        elif getvelocitydata and not gettrajectorydata: return_data.append(readHDF5(self.HDF5, mode = 1, sim_id=sim_id));

        if getmetadata: return_data.append(readParquet(self.PARQUET, sim_id=sim_id, columns = metadata))
        print("Data collected in", time()-t, "seconds")

        return return_data

    def get_last_sim_id(self): return self.last_sim_id

    def get_last_sim_track(self): return self.last_track

    def save_storage(self):
        if len(self.sim_storage) == 0: print("No sims in storage, returning..."); return
        t = time()
                
        bulksaveToParquet(filename=self.PARQUET, datadicts=[sim[1] for sim in self.sim_storage])
        bulksaveToHDF5(filename=self.HDF5, datalists=[(sim[2],sim[3]) for sim in self.sim_storage], sim_ids=[sim[0] for sim in self.sim_storage])
        save_time = time()-t
        self.save_time.append(save_time)
        print("Sims", [int(sim[0]) for sim in self.sim_storage], "saved in", save_time, "seconds")

        self.sim_storage = []
    
    def bulksavemetadata(self, datadicts):
        #Used for when you want to save metadata to parquet file in bulk from elsewhere than from within datamanager.

        bulksaveToParquet(filename=self.PARQUET, datadicts=datadicts)
    
    def deleteData(self, ids = []):
        """
        Use with caution. Because of hdf5 sorting data can get flipped around when using this method, so always check that the data you get is the data you once had by comparing the latetst backup files and the new ones. 
        
        Removes all data related to sim IDs that can be found in array ids.
        Backups data before writing to new files.

        Does not change sim_ids and because of how saveBulk methods work this will only work with deleting most recent data so the remaining data stays intact orderly.
        """

        #Metadata structure and order:
        #metadata = {
        #    "sim_id": self.last_sim_id,
        #    "sim_track": simtrack,
        #    "sim_start": simstart,
        #    "sim_end": simend,
        #    "lifespan": lifespan,
        #    "steps": args[2],
        #    "start_position": start_pos,
        #    "start_velocity": start_vel,
        #    "mass": args[5],
        #    "radius": args[6],
        #    "color": args[7],
        #    "label": args[8],
        #}

        olddata = self.get_analyze_data(sim_id = "all", metadata="all", orderMode=True)

        #Trajectorydata is treated as a dictionary, so to find sim_id 100 you just get key 100
        oldtrajectorydata = olddata[0]
        #Metadata is always treated as a dictionary of columns, so to find the mass of sim_id 100 you use the key "mass" and then the index 99.
        oldmetadata = olddata[1]

        self.backupSim(hdf5 = True, parquet = True)
        self.reset()


        newtrajectorydata = {}
        newdataDicts = []
        print(f"Old data length: {len(oldmetadata['sim_id'])}")
        for i, sim_id in enumerate(oldmetadata["sim_id"]):
            #Skip adding to newmetadata and newtrajectorydata if sim_id should be deleted.
            if sim_id in ids: continue

            newmetadata = {
                "sim_id": [],
                "sim_track": [],
                "sim_start": [],
                "sim_end": [],
                "lifespan": [],
                "steps": [],
                "start_position": [],
                "start_velocity": [],
                "mass": [],
                "radius": [],
                "color": [],
                "label": [],
            }

            #Create dict from parquet column-data.
            for key in newmetadata.keys():
                newmetadata[key] = oldmetadata[key][i]

            #Add dict to dataDicts.
            newdataDicts.append(newmetadata)

            #Add old trajectorydata to newtrajectorydata
            newtrajectorydata[sim_id] = oldtrajectorydata[sim_id]
        
        print(f"New data length: {len(newdataDicts)}")

        #Hdf5 takes data as [[traj1, vels1], [traj2, vels2], ..., [traj310, vels310]]
        datalists = [[trajdata[:6],trajdata[6:]] for trajdata in newtrajectorydata.values()]

        bulksaveToHDF5(self.HDF5, datalists=datalists, sim_ids=[dataDict["sim_id"] for dataDict in newdataDicts])

        #Parquet takes data as [metadataDict1, metadataDict2, metadataDict3, ..., metadataDict310]
        bulksaveToParquet(self.PARQUET, datadicts=newdataDicts)

        




    

#------------ Save to HDF5
def saveToHDF5(filename, datalists, sim_id: int):
    """
    Datalists: (trajectory, velocity)
    """
    #If number is below 10, add 0 before to make numerical order in .h5 file work properly. This does not impact parquet files and therefore not anything at all since sim_id is never retrieved through readHDF5. 
    if sim_id < 10:
        sim_id = "0" + str(sim_id)
    else: sim_id = str(sim_id)

    datalist = datalists[0] + datalists[1]

    #Append data to hdf5 file
    with h5py.File(filename, "a") as f:
        f["simulations"].create_dataset(sim_id, data=datalist, compression="gzip")

#------------ Save to Parquet
def saveToParquet(filename, datadict):
    dataframe = pd.DataFrame([datadict])
    
    #Concat new data to existing data
    existing = pd.read_parquet(filename)
    dataframe = pd.concat([existing, dataframe], ignore_index=True)

    #Write to file
    dataframe.to_parquet(filename, compression="zstd", index=False)

#------------ Bulk-save to HDF5
def bulksaveToHDF5(filename, datalists, sim_ids, from_delete = False):
    with h5py.File(filename, "a") as f:
        for i, sim_id in enumerate(sim_ids):
            if sim_id < 10:
                sim_id = "0" + str(sim_id)
            else: sim_id = str(sim_id)
            
            #Some datalists are as ndarrays, and those must be put together with np.concatenate.
            if type(datalists[i][0]) == list:
                datalist = datalists[i][0] + datalists[i][1]
            elif type(datalists[i][0]) == np.ndarray:
                datalist = np.concatenate((datalists[i][0], datalists[i][1]), axis=0)

            f["simulations"].create_dataset(sim_id, data=datalist, compression="gzip")

#------------ Bulk-save to parquet
def bulksaveToParquet(filename, datadicts):
    #Get existing data
    existing = pd.read_parquet(filename)

    dataframe = existing

    #Extend dataframe with new data
    for data in datadicts:
        new_dataframe = pd.DataFrame([data])
        
        dataframe = pd.concat([dataframe, new_dataframe], ignore_index=True)

    #Write dataframe to file
    dataframe.to_parquet(filename, compression="zstd", index=False)

#------------ Read HDF5
def readHDF5(filename, mode = 2, sim_id: list | str = "all", sim_track=-10, hasSimIDs = True, orderMode = False):
    """
    Docstring for readHDF5
    
    :param filename: filename
    :param mode: mode 0 - get trajectory. mode 1 - get velocity. mode 2 - get both trajectory and velocity data (default).
    :param sim_id: sim_id in a list. Always a list (except when sim_id is "all"). Default "all" => collecting from all sim_id's.
    :type sim_id: list | str
    :param sim_track: default -10, meaning disabled. Any value >0 => data retrieved sim_ids on track instead of from sim_ids.
    :type sim_track: int
    :param hasSimIDs: default True, meaning sim IDs has been retrieved and therefore shall not be retrieved in this method. Only disable if gathering data from sim track and not using parquet along with it.
    :type hasSimIDs: bool
    :param orderMode: default False, which means trajectories are retrieved normally with no thought to the order of the trajectories. If True will turn sim_id to integers and sort them along with the trajectories in a dictionary so data is sorted correctly. Only works when retrieving ALL data from h5 as of now.
    :type orderMode: bool
    """

    #Since this method doesn't return sim_id with every trajectory, there is no need to correct 01 to 1 and so on after data retrieval.

    #Returns as (for two sims) [
    # [[x11, x12,...], [y11, y12,...], [x21, x22,...], [y21, y22,...], [x31, x32,...], [y31, y32,...], [vel1x1, vel1x2, ...], [vel1y1, vel1y2, ...], [vel2x1, vel2x2, ...], [vel2y1, vel2y2, ...], [vel3x1, vel3x2, ...], [vel3y1, vel3y2, ...]], 
    # [[x11, x12,...], [y11, y12,...], [x21, x22,...], [y21, y22,...], [x31, x32,...], [y31, y32,...], [vel1x1, vel1x2, ...], [vel1y1, vel1y2, ...], [vel2x1, vel2x2, ...], [vel2y1, vel2y2, ...], [vel3x1, vel3x2, ...], [vel3y1, vel3y2, ...]],
    #]
    
    if sim_track!=-10:
        #If sim_id is "all" when using sim_track mode, it means parquet data has not been retrieved and therefore parquet file should be opened to read sim_ids. 
        # If sim_id != "all" it means the parquet file has already loaded sim_ids from sim_track and therefore the sim_ids will already be put in this function and can work like a normal retrieval of .h5 data.
        if not hasSimIDs:
            sim_id = readParquet(filename, sim_track=sim_track, columns=[])["sim_id"]

        new_sim_id = []
        for sim in sim_id:
            new_sim_id.append(sim)
        
        sim_id = new_sim_id

    return_data = []

    with h5py.File(filename, "r") as f:
        if sim_id == "all":
            if not orderMode:
                return_data = [data[()] for data in [f[f"simulations/{sim}"] for sim in f["simulations"]]]
            else:
                #This is how it should have been done from the beginning, since this is how we keep track of which sim is actually which sim. 
                return_data = {int(sim):data[()] for (data, sim) in [(f[f"simulations/{sim}"], sim) for sim in f["simulations"]]}
        else:
            #If sim_id includes numbers 1-9 add 0 before it to match how it's written in h5 file
            sim_id = ["0"+str(_id) if _id<10 else _id for _id in sim_id]
            return_data = [data[()] for data in [f[f"simulations/{sim}"] for sim in sim_id]]

    if mode == 2:
        return return_data
    elif mode == 0:
        new_return_data = []

        for sim in return_data:
            new_return_data.append(sim[:6])
        
        return new_return_data
    else:
        new_return_data = []

        for sim in return_data:
            new_return_data.append(sim[6:])
        
        return new_return_data
            
#------------ Analyze Parquet
def readParquet(filename, sim_id: list | str = "all", columns: list | str = "all", sim_track = -10):
    """
    Docstring for readParquet
    
    :param filename: filename
    :param sim_id: sim_id in a list. Always a list. Default "all" => collecting from all sim_id's.
    :type sim_id: list | str
    :param columns: list containing the columns to collect data from. Example: ("start_velocity", "start_position"). Default "all". "sim_id" included at default.
    :type columns: list | str
    :param sim_track: default -10, meaning disabled. Any value >0 => data retrieved sim_ids on track instead of from sim_ids.
    :type sim_track: int
    """

    #Returns as [
    # {colors: {parquet_row_index: [color1, color2, color3]}},
    # {}
    # ]

    #When retrieving single value from key, use next(iter(data[1]["color"].values))
    #sim_track works by retrieving all sim_ids with that sim_track and then put it into the normal code as a sim_id array.  

    data = pd.read_parquet(filename)
    if sim_track != -10:
        sim_id = data[["sim_id", "sim_track"]].query(f"sim_track in {[sim_track]}")
        sim_id = [sim for sim in sim_id["sim_id"]]

    if sim_id == "all":
        if columns == "all":
            return (data)
        else:
            columns.insert(0, "sim_id")
            return data[columns]
    else:
        if columns == "all":
            return data.query(f"sim_id in {sim_id}")
        else:
            columns.insert(0, "sim_id")
        
            #Akta dig för sql-inject haha
            return data[columns].query(f"sim_id in {sim_id}")


#------------ Transform dictionary of all data to a dictionary which can be turned into a dataframe (has two levels at max)
def dataToExcelData(dataDict, accelerations):
    velocities = dataDict["velocity"]
    dataDict.pop("trajectory")
    dataDict.pop("velocity")
    
    sim_start = dataDict["sim_start"]
    sim_end = dataDict["sim_end"]
    lifespan_list = dataDict["lifespan"]
    sim_track = int(dataDict["sim_track"])

    dataDict["lifespan"] = [int(lifespan_list[0]),int(lifespan_list[0]),int(lifespan_list[0])]
    dataDict["life_step"] = [int(lifespan_list[1]),int(lifespan_list[1]),int(lifespan_list[1])]
    dataDict["sim_track"] =[sim_track, sim_track, sim_track]
    dataDict["sim_start"] = [sim_start, sim_start, sim_start]
    dataDict["sim_end"] = [sim_end, sim_end, sim_end]

    #Data is split in two parts since the sizes of arrays need to be the same in one dataframe
    data2 = {}

    #Velocities come as x1,y1,x2,y2,x3,y3 from parquet file so here we change it to match the vx1, vx2, vx3, vy1, vy2, vy3 order of the excel document
    data2["vx1"] = velocities[0]
    data2["vx2"] = velocities[2]
    data2["vx3"] = velocities[4]
    data2["vy1"] = velocities[1]
    data2["vy2"] = velocities[3]
    data2["vy3"] = velocities[5]

    data2["ax1"] = accelerations[0]
    data2["ax2"] = accelerations[1]
    data2["ax3"] = accelerations[2]
    data2["ay1"] = accelerations[3]
    data2["ay2"] = accelerations[4]
    data2["ay3"] = accelerations[5]

    data2["steplist"] = np.arange(1, dataDict["steps"]+1)

    return dataDict, data2

        
def saveLifespanToExcel(filename, dataDict, var: str = "mass", coord: str = "all"):
    t = time()

    ldata = dataDict["lifespan"]
    sim_id = dataDict["sim_id"]
    try:
        cdata = dataDict[var]
    except:
        print("Column:", var, "not in dataDict. Returning...")
        return
    
    cd1 = []
    cd2 = []
    cd3 = []
    cd_total = []
    if var == "mass":
        for item in cdata:
            cd1.append(item[0])
            cd2.append(item[1])
            cd3.append(item[2])

            cd_total.append(item[0] + item[1] + item[2])
    
    #Currently start_position and start_velocity will just use the total for each value, i.e. x+y. 
    if var == "start_position" or var == "start_velocity":
        if coord == "all":
            for item in cdata:
                cd1.append(item[0]+item[1])
                cd2.append(item[2]+item[3])
                cd3.append(item[4]+item[5])

                cd_total.append(sum(item))
        if coord == "x":
            for item in cdata:
                cd1.append(item[0])
                cd2.append(item[2])
                cd3.append(item[4])

                cd_total.append(item[0]+item[2]+item[4])
        
        if coord == "y":
            for item in cdata:
                cd1.append(item[1])
                cd2.append(item[3])
                cd3.append(item[5])

                cd_total.append(item[1]+item[3]+item[5])
    
    ldata_formatted = []
    for data in ldata:
        ldata_formatted.append(data[0])
    
    axis1 = "Lifespan (s)"
    if var == "start_position" or var == "start_velocity":
        if coord == "all": ctext = "x+y"
        else: ctext = coord
        axis2 = f"{ctext} {var} 1"
        axis3 = f"{ctext} {var} 2"
        axis4 = f"{ctext} {var} 3"
        axis5 = f"Total {ctext} {var}"
    else:
        axis2 = f"{var} 1"
        axis3 = f"{var} 2"
        axis4 = f"{var} 3"
        axis5 = f"Total {var}"

    #print(sim_id, "\n",ldata_formatted)
    #print(cd1, "\n", cd2, "\n", cd3, "\n", cd_total)s
    df = pd.DataFrame({"sim_id": sim_id, "lifespan": ldata_formatted, f"{axis2}": cd1, f"{axis3}":cd2, f"{axis4}":cd3, f"{axis5}":cd_total})

    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        #Sheetname
        sn=f"{min(sim_id)}-{max(sim_id)}"

        df.to_excel(writer, sheet_name=sn, index=False)

        workbook = writer.book
        worksheet = writer.sheets[sn]

        max_len = len(sim_id)+1
        td = {'type': 'power', 'display_equation': True, 'forward': cd1[5]-cd1[2]}

        chart1 = workbook.add_chart({"type": "scatter"})
        chart1.add_series({
                'categories': f'={sn}!$C$2:$C${max_len}',
                'values':     f'={sn}!$B$2:$B${max_len}',
                'trendline': td,
                })
        
        chart2 = workbook.add_chart({"type": "scatter"})
        chart2.add_series({
                'categories': f'={sn}!$D$2:$D${max_len}',
                'values':     f'={sn}!$B$2:$B${max_len}',
                'trendline': td
                })
        
        chart3 = workbook.add_chart({"type": "scatter"})
        chart3.add_series({
                'categories': f'={sn}!$E$2:$E${max_len}',
                'values':     f'={sn}!$B$2:$B${max_len}',
                'trendline': td
                })

        chart4 = workbook.add_chart({"type": "scatter"})
        chart4.add_series({
                'categories': f'={sn}!$F$2:$F${max_len}',
                'values':     f'={sn}!$B$2:$B${max_len}',
                'trendline': td
                })
        
        chart1.set_title({'name': f'Lifespan vs {axis2}'})
        chart1.set_y_axis({'name': axis1})
        chart1.set_x_axis({'name': axis2})
        chart1.set_legend({'position': 'none'})
        
        chart2.set_title({'name': f'Lifespan vs {axis3}'})
        chart2.set_y_axis({'name': axis1})
        chart2.set_x_axis({'name': axis3})
        chart2.set_legend({'position': 'none'})
        
        chart3.set_title({'name': f'Lifespan vs {axis4}'})
        chart3.set_y_axis({'name': axis1})
        chart3.set_x_axis({'name': axis4})
        chart3.set_legend({'position': 'none'})

        chart4.set_title({'name': f'Lifespan vs {axis5}'})
        chart4.set_y_axis({'name': axis1})
        chart4.set_x_axis({'name': axis5})
        chart4.set_legend({'position': 'none'})

        worksheet.insert_chart('G1', chart1)
        worksheet.insert_chart('G17', chart2)
        worksheet.insert_chart('O1', chart3)
        worksheet.insert_chart('O17', chart4)

    print(f"Saved to {filename} in time", time()-t)


#------------ Save data to excel with trendlines
def saveToExcel(filename, dataDict, accelerations):
    """
    Currently only works when the data is of len 2500. 
    """
    t = time()

    data1, data2 = dataToExcelData(dataDict=dataDict, accelerations=accelerations)
    #df1 temporaly disabled as for some reason it does not work with the parameters that was added since the initial creation of the method
    #df1 = pd.DataFrame(data1)
    df2 = pd.DataFrame(data2)

    steps = data1["steps"]
    #Somehow vx2 and vy1 switched places so the data in excel is wrong. Please look for where this error occurs and fix it after you're done with acctol shit

    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        #Sheetname
        sn = f"{data1['sim_id']}"

        df2.to_excel(writer, sheet_name=sn, index=False)
        #df1.to_excel(writer, sheet_name="Metadata", index=False)

        workbook = writer.book
        worksheet = writer.sheets[sn]

        axis1 = "Acceleration (m/s^2)"
        axis2 = "Velocity (m/s)"

        chart1x = workbook.add_chart({"type": "scatter"})
        chart2x = workbook.add_chart({"type": "scatter"})
        chart3x = workbook.add_chart({"type": "scatter"})
        chart1y = workbook.add_chart({"type": "scatter"})
        chart2y = workbook.add_chart({"type": "scatter"})
        chart3y = workbook.add_chart({"type": "scatter"})

        chartv1x = workbook.add_chart({"type": "scatter"})
        chartv2x = workbook.add_chart({"type": "scatter"})
        chartv3x = workbook.add_chart({"type": "scatter"})
        chartv1y = workbook.add_chart({"type": "scatter"})
        chartv2y = workbook.add_chart({"type": "scatter"})
        chartv3y = workbook.add_chart({"type": "scatter"})
    
        def get_series(chart1x,chart2x,chart3x,chart1y,chart2y,chart3y,chartv1x,chartv2x,chartv3x,chartv1y,chartv2y,chartv3y,steps):
            chart1x.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$G$2:$G$2501',
                })
            
            chart2x.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$H$2:$H$2501',
                })
            
            chart3x.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$I$2:$I$2501',
                })
            
            chart1y.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$J$2:$J$2501',
                })
            
            chart2y.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$K$2:$K$2501',
                })
            
            chart3y.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$L$2:$L$2501',
                })

            chart1x.set_title({'name': 'X acceleration of Body 1 vs Steps'})
            chart1x.set_y_axis({'name': axis1})

            chart2x.set_title({'name': 'X acceleration of Body 2 vs Steps'})
            chart2x.set_y_axis({'name': axis1})

            chart3x.set_title({'name': 'X acceleration of Body 3 vs Steps'})
            chart3x.set_y_axis({'name': axis1})

            chart1y.set_title({'name': 'Y acceleration of Body 1 vs Steps'})
            chart1y.set_y_axis({'name': axis1})

            chart2y.set_title({'name': 'Y acceleration of Body 2 vs Steps'})
            chart2y.set_y_axis({'name': axis1})

            chart3y.set_title({'name': 'Y acceleration of Body 3 vs Steps'})
            chart3y.set_y_axis({'name': axis1})

            chartv1x.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$A$2:$A$2501',
                })
            
            chartv2x.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$B$2:$B$2501',
                })
            
            chartv3x.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$C$2:$C$2501',
                })
            
            chartv1y.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$D$2:$D$2501',
                })
            
            chartv2y.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$E$2:$E$2501',
                })
            
            chartv3y.add_series({
                'categories': f'={sn}!$M$2:$M$2501',
                'values':     f'={sn}!$F$2:$F$2501',
                })
            
            chartv1x.set_title({'name': 'X velocity of Body 1 vs Steps'})
            chartv1x.set_y_axis({'name': axis2})

            chartv2x.set_title({'name': 'X velocity of Body 2 vs Steps'})
            chartv2x.set_y_axis({'name': axis2})

            chartv3x.set_title({'name': 'X velocity of Body 3 vs Steps'})
            chartv3x.set_y_axis({'name': axis2})

            chartv1y.set_title({'name': 'Y velocity of Body 1 vs Steps'})
            chartv1y.set_y_axis({'name': axis2})

            chartv2y.set_title({'name': 'Y velocity of Body 2 vs Steps'})
            chartv2y.set_y_axis({'name': axis2})

            chartv3y.set_title({'name': 'Y velocity of Body 3 vs Steps'})
            chartv3y.set_y_axis({'name': axis2})

            charts = [chart1x, chart2x, chart3x, chart1y, chart2y, chart3y, chartv1x, chartv2x, chartv3x, chartv1y, chartv2y, chartv3y]

            for chart in charts:
                chart.set_legend({'position': 'none'})
                chart.set_x_axis({'name': 'Steps', "min": 0, "max": steps})
            
            return charts

        chart1x, chart2x, chart3x, chart1y, chart2y, chart3y, chartv1x, chartv2x, chartv3x, chartv1y, chartv2y, chartv3y = get_series(chart1x, chart2x, chart3x, chart1y, chart2y, chart3y, chartv1x, chartv2x, chartv3x, chartv1y, chartv2y, chartv3y, steps=steps)

        worksheet.insert_chart('N2', chart1x)
        worksheet.insert_chart('N17', chart2x)
        worksheet.insert_chart('N32', chart3x)
        worksheet.insert_chart('V2', chart1y)
        worksheet.insert_chart('V17', chart2y)
        worksheet.insert_chart('V32', chart3y)

        worksheet.insert_chart('AD2', chartv1x)
        worksheet.insert_chart('AD17', chartv2x)
        worksheet.insert_chart('AD32', chartv3x)
        worksheet.insert_chart('AL2', chartv1y)
        worksheet.insert_chart('AL17', chartv2y)
        worksheet.insert_chart('AL32', chartv3y)
    
    print(f"Saved to {filename} in time", time()-t)

if __name__ == "__main__":
    dm = DataManager(reset=False)

    #dm.saveSim()

    olddata = dm.get_analyze_data(sim_id = "all", metadata="all", orderMode = True)

    #Trajectorydata is always treated as an array, so to find sim_id 100 you just get index 99 of the array.
    oldtrajectorydata = olddata[0]
    #Metadata is always treated as a dictionary of columns, so to find the mass of sim_id 100 you use the key "mass" and then the index 99.
    oldmetadata = olddata[1]

    print(len(oldtrajectorydata.keys()))

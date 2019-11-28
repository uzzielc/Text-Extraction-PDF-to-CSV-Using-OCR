'''
** NOTES **
- This python script will scan the current directory for png files.

- Once the png files are found, it will run pytesseract to extract the text.

- The text is then parsed for fields of the form '%:'.

- Looping through the fields, it will create bounding boxes from the fields
    adjacent to the current field and extract any text in the bounding box.

- SPECIAL CASES:
    - Sometimes current fields do not have adjacent fields of the form '%:'.

    - We handle this by hard coding the adjacent fields or bounding boxes.

- Once the text for each field is extracted, we store the current field
    and corresponding text in a dictionary for final output

- The dictionary is mapped to the new target field names and we create a .csv file

# All comments in this file refer to the code directly below the comment
'''
import csv
import pytesseract
import cv2
import pandas as pd
import numpy as np
import os
import PIL
from wand.image import Image
from wand.display import display
import time
pd.set_option('display.max_rows', None)

filenames = []

def getPdfTextData():
    # Scan the current directory for the .pdf file that will be converted
    for file_ in os.scandir(os.getcwd()):
        if file_.name.endswith('.pdf'):
            filenames.append(file_.name)

    # Load the .pdf file and save as .png
    DPI = 600
    pdf = Image(filename = filenames[0], resolution = DPI)
    png_files = []
    for page_num,page in enumerate(pdf.sequence):
        page = Image(page)
        page = page.convert('png')
        temp_file_name = 'temp_' + str(page_num) + '.png'
        png_files.append(temp_file_name)
        page.save(filename = temp_file_name)

    # Load the .png files and combine to make one image
    img_arrays = []
    #if len(png_files) > 1:
    for file_ in (png_files):
        # open the first image file
        img = cv2.imread(file_)
        sz = img.shape
        start_row = round(0.05 * sz[0])
        end_row = sz[0] - start_row
        # convert the image to numpy array
        img_arrays.append(np.array(img))#[start_row:end_row,:,:]))
        # delete the temporary png file that we just read
        os.remove(file_)
    final_img_arr = np.vstack(img_arrays)

    img = PIL.Image.fromarray(final_img_arr).convert('L')
    threshold = 200
    img = img.point(lambda p: p > threshold and 255)
    img.show()

    # this is where we will temporarily store the extracted text
    tsv_filename = "text.tsv" 
    # Get TSV information about the text and write the temp file
    # --psm 3 or --psm 6 or --psm 11 is working well
    custom_oem_psm_config = r'--psm 3'
    text = pytesseract.image_to_data(img, config = custom_oem_psm_config)
    file_object = open(tsv_filename,'w')
    file_object.write(text)
    file_object.close()

    # Read the TSV .txt file into a pandas dataframe
    csv_table=pd.read_table(tsv_filename,sep='\t')
    # delete the TSV (.txt) file we created above now that the data is read into pd
    os.remove(tsv_filename)
    # Drop the rows with NaN values
    csv_table = csv_table.dropna()
    csv_table = csv_table.reset_index(drop = True)


    # Clean the image

    # DOCUMENT TYPE 1
    #Physician Referral - Print View                            https://prs.choosebroadspire.com/Template.aspx?PRSId=20191115... (Top)
    #1 of 4                                                     11/15/19, 2:22 PM  (Always on Bottom)

    # DOCUMENT TYPE 2
    #11/8/2019                                                  Physician Referral - Print View (Always on top)
    #https://prs.choosebroadspire.com/Template.a...             1/2 (Always on bottom)
    
    # Remove timestamps, datestamps, and website stamps
    # Find and drop the lines of text that match regular expressions like:
    #   - reg_expr = 'http://%'
    #   - reg_expr = '[0-1][0-9]/[0-3][0-9]/[0-9][0-9], [0-12]+:[0-5][0-9] [AP]M'

    print(csv_table)
    # if document is of type 1
    if csv_table.text.values[0] == 'Physician':
        cond_line1 = csv_table.text.str.contains('https://.*',regex=True)
        cond_line2 = csv_table.text.str.contains('[0-9]{1,2}/[0-9]{1,2}/[0-9]{1,2},',regex=True)

        line1_tops = csv_table[cond_line1].top.values
        line1_heights = csv_table[cond_line1].height.values

        line2_tops = csv_table[cond_line2].top.values
        line2_heights = csv_table[cond_line2].height.values

        # now that we have the top of the bounding boxes for each line
        # lets search through all other entries in the data frame that 
        # have tops in a small interval around the top of lines of interest
        for top1,top2,height1,height2 in zip(line1_tops,line2_tops,line1_heights,line2_heights):
            cond11 = csv_table['top'].ge(top1 - height1 * 0.7)
            cond12 = csv_table['top'].le(top1 + height1 * 0.7)
            line1_table = csv_table[cond11 & cond12]

            #get the indices for the table above and drop them from the final table
            cond21 = csv_table['top'].ge(top2 - height2 * 0.7)
            cond22 = csv_table['top'].le(top2 + height2 * 0.7)
            line2_table = csv_table[cond21 & cond22]

            line1_indices = line1_table.index.values
            line2_indices = line2_table.index.values
            csv_table = csv_table.drop(index = line1_indices)
            csv_table = csv_table.drop(index = line2_indices)
            
            csv_table = csv_table.reset_index(drop = True)

    # if document is of type 2
    if csv_table.head(1).text.str.contains('[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}',regex=True).values[0]:
        # Because document of type 2 have header lines we want to remove containing dates,
        # we need to be careful not to delete other lines within the document that contain dates.
        # To do this, we find all strings that have the date form and filter those by adding the contstraint
        # that the next index in the table should be Physician Referral

        # get all a table with matches for dates
        dates_cond = csv_table.text.str.contains('[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}',regex=True)
        dates_indices = csv_table[dates_cond].index.values
        dates_indices1 = dates_indices.tolist()

        line1_tops = []
        line1_heights = []
        for index in dates_indices:
            if csv_table.at[index + 1,'text'] == 'Physician' and csv_table.at[index + 2,'text'] == 'Referral':
                line1_tops.append(csv_table.at[index,'top'])
                line1_heights.append(csv_table.at[index,'height'])
            else:
               continue
        
        cond_line2 = csv_table.text.str.contains('https://.*',regex=True)

        line2_tops = csv_table[cond_line2].top.values
        line2_heights = csv_table[cond_line2].height.values

        # now that we have the top of the bounding boxes for each line
        # lets search through all other entries in the data frame that 
        # have tops in a small interval around the top of lines of interest
        print('********')
        print(line1_tops)
        print(line1_heights)
        print(line2_tops)
        print(line2_heights)
        for top1,top2,height1,height2 in zip(line1_tops,line2_tops,line1_heights,line2_heights):
            print('****')
            cond11 = csv_table['top'].ge(top1 - height1 * 0.7)
            cond12 = csv_table['top'].le(top1 + height1 * 0.7)
            line1_table = csv_table[cond11 & cond12]
            line1_indices = line1_table.index.values
            print(line1_indices)
            csv_table = csv_table.drop(index = line1_indices)
            csv_table = csv_table.reset_index(drop = True)


            #get the indices for the table above and drop them from the final table
            cond21 = csv_table['top'].ge(top2 - height2 * 0.7)
            cond22 = csv_table['top'].le(top2 + height2 * 0.7)
            line2_table = csv_table[cond21 & cond22]
            line2_indices = line2_table.index.values
            print(line2_indices)
            csv_table = csv_table.drop(index = line2_indices)
            csv_table = csv_table.reset_index(drop = True)

    return csv_table

def groupMicroFields(csv_table):
    # Going through each page, block, and horizontal line,
    # look for words with a colon and determine whether
    # or not they need to be grouped with previous words
    for page_number in np.unique(csv_table.page_num):
        table1 = csv_table[csv_table.page_num == page_number]
        for block_number in np.unique(table1.block_num):
            table2 = table1[table1.block_num == block_number]
            for par_number in np.unique(table2.par_num):
                table3 = table2[table2.par_num == par_number]
                for line_number in np.unique(table3.line_num):
                    table4 = table3[table3.line_num == line_number]
                    word_nums = []
                    # now table for contains the parsed text contained in ONE line of the document.
                    # we will use this to start grouping text based together
                    for word_number in np.unique(table4.word_num):
                        word_nums.append(word_number)
                        text = table4[table4.word_num == word_number].text.values[0]
                        #print(table4)
                        if text.endswith(':'):
                            first_word_number = word_nums[0]
                            word_nums.remove(first_word_number)
                            index_to_cat_to = table4[table4.word_num == first_word_number].index[0]
                            for number in word_nums:
                                # get the text
                                temp_text = table4[table4.word_num == number].text.values[0]
                                temp_width = table4[table4.word_num == number].width.values[0]
                                csv_table = csv_table.drop(table4[table4.word_num == number].index[0])
                                # concatenate the text 
                                csv_table.at[index_to_cat_to,'text'] = csv_table.at[index_to_cat_to,'text'] + ' ' + temp_text
                                csv_table.at[index_to_cat_to, 'width'] = csv_table.at[index_to_cat_to,'width'] + temp_width
                            word_nums = []

    csv_table = csv_table.reset_index(drop = True)
    return csv_table

def groupMacroFields(csv_table,macro_fields):
    # set up some important fields that will be critical in constructing bounding boxes later
    for field in macro_fields:
        first_word = field.split(' ')
        first_word = first_word[0]
        reviewing_indices = csv_table[csv_table.text == first_word].index.values
        reviewing_indices = reviewing_indices.tolist()
        num_words = field.count(' ') + 1
        #print('Field: ',field)
        #print('String Length:',len(field))
        #print(reviewing_indices)
        for index in reviewing_indices:
            # build the string
            string_ = ''
            index_list = list(range(index,index+num_words))
            for i in index_list:
                string_ = string_ + csv_table.at[i,'text'] + ' '
            string_ = string_.strip()
            if field != string_:
                #print('String_: ',string_)
                #print('String Length: ',len(string_))
                #print('continue')
                continue
            else:
                #print('String_: ',string_)
                #print('String_ Length: ', len(string_))
                #print('else')
                csv_table.at[index,'text'] = string_
                index_list.pop(index_list.index(index))
                csv_table = csv_table.drop(index = index_list)
                break
    return csv_table

def findRightField(csv_table,field,left,top,width,height):
    # find the field to the right
    cond1 = csv_table['left'].gt(left)
    cond2 = csv_table['top'].ge(top - 0.5 * char_width)
    cond3 = csv_table['top'].le(top + 0.5 * char_width)
    
    # The next try block will throw in error in some cases (such as when field == 'Referral Type:')
    # because there is no field to the right. In this case, we catch the expection and manually define 
    # the right side of the bounding box.
    try:
        # if there is a right field, get the bounding box
        right_field = csv_table[cond1 & cond2 & cond3].text.values[0]
        #print(csv_table[cond1 & cond2 & cond3])
        right_field_left = csv_table[csv_table.text == right_field].left.values[0] - char_width
        #print('*',right_field,'*')
        # special case for Diagnosis / Compensable text box
        if field in ('Diagnosis','Compensable','Records'):
            right_field_left = sz[0]
            #print('if')
    except:
        # if there is no right field, multiply the width and use that for bounding box
        right_field_left = left + width * 10
        #print('exception right field')
    return right_field_left

def findBottomField(csv_table,field,left,top,width,height):
    # find the field below
    cond12 = csv_table['top'].ge(top+5)
    cond22 = csv_table['left'].ge(left - 4 * char_width)
    cond32 = csv_table['left'].lt(left + 4 * char_width)
    table = csv_table[cond12 & cond22 & cond32]
    cond = table.text.str.contains(':$',regex=True)

    # The next try block will throw in error in some cases (such as when field == 'Physician Reviewer:')
    # because there is no field below. In this case, we catch the expection and manually define 
    # the top side of the bounding box.
    # special cases where bottom field does not end with ':' or there is unwanted text between fields
    if field in ('Claim Benefit State:','Sex:'):
        bottom_field = 'Diagnosis'
        #print('**',bottom_field,'**')
    elif field == 'Diagnosis':
        bottom_field = 'Line of Business:'
        #print('**',bottom_field,'**')
    elif field in ('Line of Business:','Date Of Injury:'):
        bottom_field = 'Compensable'
        #print('**',bottom_field,'**')
    elif field == 'Compensable':
        bottom_field = 'Reviewing Physician Data'
        #print('**',bottom_field,'**')
    elif field in ('Specialty:', 'Physician Reviewer:'):
        bottom_field = 'Records Submitted for Review'
        #print('**',bottom_field,'**')
    elif field == 'Records Submitted for Review':
        bottom_field = 'Referral Questions And Conclusions'
        #print('**',bottom_field,'**')
    else:
        try:
            bottom_field = table[cond].text.values[0]
            #print('**',bottom_field,'**')
        except Exception as err:
            #print('Exception Caught in findBottomField:')
            #print('No bottom field found for:',field)
            #print('Bottom field top is set to deafault of 3 lines')
            bottom_field_top = top + height * 2.1
            return bottom_field_top


    bottom_field_top = csv_table[csv_table.text == bottom_field].top.values[0]
    return bottom_field_top

def findBoundedText(csv_table,field,left,top,right_field_left,bottom_field_top):
    # find all text within the box bounded by:
    # [left,top], [left, bottom_field_top], [right_field_left,top], [right_field_left,bottom_field_top]
    cond1 = csv_table['left'].gt(left - char_width)
    cond2 = csv_table['left'].lt(right_field_left - char_width)
    cond3 = csv_table['top'].lt(bottom_field_top - 0.2 * height)
    cond4 = csv_table['top'].gt(top + 0.5 * char_width)



    table1 = csv_table[cond1 & cond2 & cond3 & cond4]
    print(field)
    print(table1)
    if field in ('Diagnosis','Records Submitted for Review','Claim Number:'):
        values = []
        for block_number in np.unique(table1.block_num):
            table2 = table1[table1.block_num == block_number]
            for par_number in np.unique(table2.par_num):
                table3 = table2[table2.par_num == par_number]
                for line_number in np.unique(table3.line_num):
                    table4 = table3[table3.line_num == line_number]
                    temp_string = ''
                    for word in table4.text:
                        temp_string = temp_string + ' ' + word
                    values.append(temp_string + '\n')
    else:
        values = csv_table[cond1 & cond2 & cond3 & cond4].text.values

    if len(values) > 1:
        temp_string = ''
        for string in values:
            temp_string = temp_string + ' ' + string
        values = [temp_string.strip()]
    return values

def createFinalDictionary():
    final_dict = {}
    target_input_map = {}
    for x,y in zip(input_fields,target_fields):
        target_input_map.update({y:x})
    for key in target_fields:
        key2 = target_input_map[key]
        print(key,': ',fields_values[key2])
        final_dict.update({key:fields_values[key2]})
    return final_dict

def writeCSV(final_dict):
    file_str = filenames[0]
    file_str = file_str.replace('.pdf','')
    csv_filename = file_str + '.csv'
    with open(csv_filename, 'w', newline="") as csv_file:  
        writer = csv.writer(csv_file)
        for key, value in final_dict.items():
            writer.writerow([key, value])

# set up the input fields ( fields in .pdf file)
# set up the target fields ( fields in the .csv file)
input_fields = [
    'PRS ID Number:',
    'Due Date:',
    'Review Type:',
    'Requested By:',
    'Company Name:',
    'Claim Number:',
    'Claimant First Name:',
    'Claimant Last Name:',
    'Date of Birth:',
    'Sex:',
    'Claim Benefit State:',
    'Diagnosis',
    'Line of Business:',
    'Date Of Injury:',
    'Compensable',
    'Specialty:',
    'Physician Reviewer:',
    'Records Submitted for Review'
    ]

target_fields = [
    'Client ID',
    'Client Due Date',
    'Referral Type',
    'Requestor',
    'Sub Client',
    'Claim #',
    'First Name',
    'Last Name',
    'DOB',
    'Gender',
    'Jurisdictional State',
    'Diagnosis',
    'Client Form',
    'DOI',
    'Compensable Body Part',
    'Specialty',
    'Reviewer Assignment',
    'Notes for Reviewer:/ Administrative Notes'
    ]

macro_fields = [
    'Referral Information',
    'Claim Data',
    'Reviewing Physician Data',
    'Records Submitted for Review',
    'Referral Questions And Conclusions'
    ]


csv_table = getPdfTextData()

# get width of one character for proper filtering later
temp_string = csv_table[csv_table.text == 'Referral'].text.values[0]
char_width = round(csv_table[csv_table.text == 'Referral'].width.values[0] / len(temp_string))
#print(csv_table)

csv_table = groupMacroFields(csv_table,macro_fields)
csv_table = groupMicroFields(csv_table)
fields_values = {}
# for each field, look to see what field is to the right & below and get thier left and top respectively
for field in input_fields:
    # get coordinate information for the current field of interest
    print('*****',csv_table[csv_table.text == field].text.values[0],'*****')
    left = csv_table[csv_table.text == field].left.values[0]
    top = csv_table[csv_table.text == field].top.values[0]
    width = csv_table[csv_table.text == field].width.values[0]
    height = csv_table[csv_table.text == field].height.values[0]
    
    right_field_left = findRightField(csv_table,field,left,top,width,height)
    
    bottom_field_top = findBottomField(csv_table,field,left,top,width,height)

    values = findBoundedText(csv_table,field,left,top,right_field_left,bottom_field_top)
    
    fields_values.update({field:values[0]})

final_dict = createFinalDictionary()
writeCSV(final_dict)
